"""Independent technical checks of produced demo artifacts and preserved sources."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory.config import Config
from factory.db import DB
from factory.media import heavy_lock, executable, probe

def run(data,preview_only=False):
    data=Path(data).resolve()
    config=Config(data=data)
    db=DB(data/'factory.sqlite3')
    videos=db.all("SELECT a.path,v.id FROM video_jobs v JOIN assets a ON a.id=v.final_asset_id WHERE v.output_status='RENDERED' ORDER BY v.created_at")
    assert videos,'No rendered videos'
    qa=data/'qa';qa.mkdir(exist_ok=True)
    with heavy_lock():
        if not preview_only:
            assert len(videos)==12,f'Expected 2 A + 10 B masters, got {len(videos)}'
            for v in videos:
                info=probe(Path(v['path']),config,30)
                assert info['streams'][0]['pix_fmt']=='yuv420p'
                packets=json.loads(subprocess.check_output([executable('ffprobe',config.ffprobe),'-v','error','-select_streams','v:0','-show_entries','packet=pts_time,dts_time','-of','json',v['path']],creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))['packets']
                assert len(packets)==900
                dts=[float(p['dts_time']) for p in packets]
                assert all(a<b for a,b in zip(dts,dts[1:]))
                pts=sorted(float(p['pts_time']) for p in packets)
                assert all(abs(t-i/30)<.002 for i,t in enumerate(pts))
            baseline=json.loads((ROOT/'data/baseline/manifest.json').read_text())
            allowed={'Remotion\\tools\\render-case.mjs'}
            for name,digest in baseline.items():
                if name not in allowed:
                    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Baseline modified: {name}'
            keys=db.all('SELECT avatar_clip_asset_id,screencast_asset_id,hook_id,scenario_id,scenario_version,creative_revision FROM combinations')
            assert len({tuple(k.values()) for k in keys})==len(keys)
        images=[]
        for i,seconds in enumerate((1.5,7,13,21,28.5)):
            target=qa/f'preview-{i}.png'
            subprocess.run([executable('ffmpeg',config.ffmpeg),'-v','error','-y','-ss',str(seconds),'-i',videos[0]['path'],'-frames:v','1',str(target)],check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            with Image.open(target) as im:
                thumb=im.convert('RGB');thumb.thumbnail((270,480));images.append(thumb)
        sheet=Image.new('RGB',(1350,510),'white')
        draw=ImageDraw.Draw(sheet)
        for i,im in enumerate(images):
            sheet.paste(im,(270*i,30));draw.text((270*i+5,8),f'{(1.5,7,13,21,28.5)[i]}s',fill='black')
        sheet.save(qa/'montage-preview.jpg')
    result={'checked_masters':0 if preview_only else len(videos),'preview':str(qa/'montage-preview.jpg'),'source_preservation':'not checked while rendering' if preview_only else 'PASS (only CLI adapter changed)','timestamps':'not checked' if preview_only else 'PASS: 900 frames, monotonic DTS, 30 fps PTS grid'}
    if not preview_only:
        (qa/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('data');parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args();run(args.data,args.preview_only)
