"""A real local media E2E, with explicitly simulated AI and review decisions."""
import asyncio
import hashlib
import json
import shutil
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .config import Config, ROOT
from .db import uid
from .engine import Factory
from .fake_worker import FakeWorker, serve
from .bot import FakeGateway, flush_notifications
from .media import executable, heavy_lock, process, probe

def seed_demo(factory):
    root=factory.config.data/'imports'
    root.mkdir(parents=True,exist_ok=True)
    assets=ROOT/'Remotion/public/assets'
    originals=[assets/'original.jpg',assets/'reference.jpg']+[assets/f'gallery-{i}.jpg' for i in range(1,9)]
    references=[assets/'reference.jpg',assets/'gallery-7.jpg']+[assets/f'gallery-{i}.jpg' for i in range(2,10)]
    pairs=[]
    for i,(original,ref) in enumerate(zip(originals,references)):
        o,r=root/f'original-{i}.jpg',root/f'reference-{i}.jpg'
        for source,dest in ((original,o),(ref,r)):
            if not dest.exists():
                shutil.copy2(source,dest)
        pairs.append({'id':f'demo-pair-{i:02d}','original':o.name,'reference':r.name,'rights_status':'test-only','tags':['demo']})
    manifest=root/'manifest.json'
    manifest.write_text(json.dumps({'pairs':pairs},indent=2),encoding='utf-8')
    factory.library.import_manifest(manifest)
    for n,color in enumerate(('#173d4c','#49274b'),1):
        still,clip=root/f'avatar-{n}.png',root/f'avatar-{n}.mp4'
        if not clip.exists():
            image=Image.new('RGB',(1080,1920),color)
            draw=ImageDraw.Draw(image)
            font=ImageFont.truetype('arial.ttf',64)
            small=ImageFont.truetype('arial.ttf',36)
            draw.ellipse((290,480,790,980),fill='#55c5b9')
            draw.ellipse((390,630,440,680),fill='white')
            draw.ellipse((640,630,690,680),fill='white')
            draw.arc((430,660,650,850),0,180,fill='white',width=15)
            draw.text((540,1100),'VIBE COPY',font=font,fill='white',anchor='mm')
            draw.text((540,1450),'MOCK / TECHNICAL AVATAR',font=small,fill='white',anchor='mm')
            image.save(still)
            with heavy_lock():
                process([executable('ffmpeg',factory.config.ffmpeg),'-hide_banner','-y','-loop','1','-i',still,'-vf',"zoompan=z='1+0.0005*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=90:s=1080x1920:fps=30,format=yuv420p",'-t','3','-an','-c:v','libx264','-preset','veryfast','-threads','2',clip],root,root/f'avatar-{n}.log',factory.config.data/'logs/performance.jsonl')
            probe(clip,factory.config,3)
        factory.library.add(clip.read_bytes(),'animated_avatar','video/mp4','APPROVED','test-only',metadata={'mock':True,'technical_fixture':True})

def sample_digest(config,video,seconds,destination):
    import subprocess
    with heavy_lock():
        subprocess.run([executable('ffmpeg',config.ffmpeg),'-v','error','-y','-ss',str(seconds),'-i',str(video),'-frames:v','1',str(destination)],check=True,creationflags=subprocess.CREATE_NO_WINDOW if __import__('os').name=='nt' else 0)
    with Image.open(destination) as im:
        return hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()

async def verify_remotion(factory,cases):
    results=[]
    storyboard=[]
    for case in cases:
        pair=factory.db.one('SELECT * FROM photo_pairs WHERE id=?',(case['pair_id'],))
        photos={k:factory.library.file(v) for k,v in {'original':pair['original_asset_id'],'reference':pair['reference_asset_id'],'result':case['result_asset_id']}.items()}
        before={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in photos.items()}
        original_work=factory.config.data/'work'/case['id']
        repeat_work=factory.config.data/'work/verification'/case['id']
        output=repeat_work/'screencast.mp4'
        timeline=None
        if output.exists() and (repeat_work/'timeline.json').exists():
            try:
                probe(output,factory.config,24)
                timeline=json.loads((repeat_work/'timeline.json').read_text())
            except Exception:
                timeline=None
        if timeline is None:
            output,timeline=await asyncio.to_thread(factory.remotion.render,case['id'],photos,repeat_work)
        digests=[]
        for stage in ('original','reference','result'):
            event=timeline['stages'][stage]
            seconds=(event['start']+event['length']*.8)/30
            first=await asyncio.to_thread(sample_digest,factory.config,original_work/'screencast.mp4',seconds,repeat_work/f'{stage}-first.png')
            again=await asyncio.to_thread(sample_digest,factory.config,output,seconds,repeat_work/f'{stage}-repeat.png')
            if first!=again:
                raise AssertionError('Repeated Remotion frames differ')
            digests.append(first)
            with Image.open(repeat_work/f'{stage}-repeat.png') as im:
                thumb=im.convert('RGB');thumb.thumbnail((270,480));storyboard.append(thumb)
        assert before=={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in photos.items()}
        results.append({'case_id':case['id'],'source_hashes':before,'frame_hashes':digests,'repeat':str(output)})
    assert results[0]['frame_hashes']!=results[1]['frame_hashes']
    sheet=Image.new('RGB',(810,960),'white')
    for i,im in enumerate(storyboard):
        sheet.paste(im,((i%3)*270,(i//3)*480))
    sheet.save(factory.config.data/'remotion-verification.jpg')
    return results

async def demo(resume=None,verify=False):
    started=time.monotonic()
    data=Path(resume).resolve() if resume else ROOT/'data/demo'/uid()
    config=Config(data=data,admin_ids=(4242,))
    factory=Factory(config)
    factory.composer.doctor()
    print('DEMO_DATA='+str(data),flush=True)
    state_path=data/'demo-state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    def save():
        state_path.write_text(json.dumps(state,indent=2),encoding='utf-8')
    await asyncio.to_thread(seed_demo,factory)
    worker=FakeWorker(data/'fake-worker.sqlite3')
    gateway=FakeGateway()
    async with serve(worker) as url:
        config.worker_url=url
        if not state.get('batch_a'):
            state['batch_a']=factory.start_a();save()
        if resume:
            for job in factory.db.all("SELECT * FROM queue_jobs WHERE status='FAILED'"):
                factory.resume(job['id'])
        await factory.drain('processing')
        await flush_notifications(factory,gateway)
        slots=factory.db.all('SELECT * FROM batch_slots WHERE batch_id=? ORDER BY slot_no',(state['batch_a'],))
        assert len(slots)==10
        for i in range(2):
            case=factory.db.one('SELECT * FROM cases WHERE id=?',(slots[i]['case_id'],))
            print(f'Mode A: approve demo slot {i+1}; render real screencast + master',flush=True)
            factory.review_case(case['id'],'approve')
            await factory.drain('heavy')
            if i==0 and 'immediate_approval_proof' not in state:
                pending=factory.db.one("SELECT count(*) n FROM cases WHERE status='PENDING_REVIEW'")['n']
                assert pending==9
                state['immediate_approval_proof']={'other_candidates_pending':pending};save()
            video=factory.db.one('SELECT v.* FROM video_jobs v JOIN combinations c ON c.id=v.combination_id WHERE c.slot_id=? ORDER BY v.created_at DESC LIMIT 1',(slots[i]['id'],))
            await flush_notifications(factory,gateway)
            factory.review_video(video['id'],'approve')
        third=factory.db.one('SELECT * FROM cases WHERE id=?',(slots[2]['case_id'],))
        if slots[2]['attempt_no']==1 and third['status']=='PENDING_REVIEW':
            state['retry_old_request_id']=third['processing_request_id'];save()
            factory.review_case(third['id'],'retry',1)
        await factory.drain('processing')
        third=factory.db.one('SELECT * FROM cases WHERE id=?',(slots[2]['case_id'],))
        assert third['processing_request_id']!=state['retry_old_request_id']
        for slot in slots[2:]:
            factory.review_case(slot['case_id'],'reject-final')
        assert factory.db.one('SELECT * FROM batches WHERE id=?',(state['batch_a'],))['status']=='PARTIAL'
        if verify and 'remotion_verification' not in state:
            cases=[factory.db.one('SELECT * FROM cases WHERE id=?',(s['case_id'],)) for s in slots[:2]]
            print('Verify both photo triples a second time (real Remotion)',flush=True)
            state['remotion_verification']=await verify_remotion(factory,cases);save()
        if not state.get('batch_b'):
            state['batch_b']=factory.start_b();save()
        before=worker.calls
        print('Mode B: compose 10 unique real masters from approved cache; zero AI',flush=True)
        await factory.drain('heavy')
        assert worker.calls==before
        videos=factory.db.all('SELECT v.* FROM video_jobs v JOIN combinations c ON c.id=v.combination_id WHERE c.batch_id=?',(state['batch_b'],))
        assert len(videos)==10 and all(v['output_status']=='RENDERED' for v in videos)
        await flush_notifications(factory,gateway)
        for v in videos:
            factory.review_video(v['id'],'approve')
            await asyncio.to_thread(probe,factory.library.file(v['final_asset_id']),config,30)
        assert factory.db.one('SELECT * FROM batches WHERE id=?',(state['batch_b'],))['status']=='COMPLETED'
        master=data/'demo-master.mp4'
        shutil.copy2(factory.library.file(videos[0]['final_asset_id']),master)
        exports=data/'exports'
        exports.mkdir(exist_ok=True)
        outputs=[]
        for row in factory.db.all('SELECT b.mode,b.id batch_id,s.slot_no,v.id video_id,a.path,a.sha256 FROM video_jobs v JOIN combinations c ON c.id=v.combination_id JOIN batches b ON b.id=c.batch_id JOIN batch_slots s ON s.id=c.slot_id JOIN assets a ON a.id=v.final_asset_id WHERE v.output_status=\'RENDERED\' AND v.review_status=\'APPROVED\' ORDER BY b.mode,s.slot_no'):
            target=exports/f"{row['mode']}-{row['slot_no']:02d}-{row['sha256'][:8]}.mp4"
            if not target.exists():
                shutil.copy2(row['path'],target)
            outputs.append({**row,'export':str(target)})
        perf=[json.loads(line) for line in (data/'logs/performance.jsonl').read_text().splitlines()]
        report={'integration':'MOCK','real_paid_calls':0,'reviews':'SCRIPTED TEST DECISIONS; human creative review pending','fake_worker_calls':worker.calls,'mode_b_fake_calls':worker.calls-before,'batch_a':state['batch_a'],'batch_b':state['batch_b'],'master':str(master),'outputs':outputs,'elapsed_this_invocation_seconds':round(time.monotonic()-started,2),'heavy_elapsed_seconds_sum':round(sum(p['elapsed_seconds'] for p in perf),2),'peak_process_tree_rss_bytes':max(p['peak_tree_rss_bytes'] for p in perf),'memory_measurement':'sum of process-tree RSS; excludes OS and other applications','heavy_processes':len(perf),'mock_telegram_messages_this_invocation':len(gateway.messages),'proofs':state,'status':factory.status()}
        (data/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
        return report
