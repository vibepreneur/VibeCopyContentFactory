from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time
import psutil
from .config import Config, ROOT

def executable(name, override=''):
    if override:
        path=Path(override).resolve()
        if not path.is_file():
            raise RuntimeError(f'{name} override missing')
        return str(path)
    candidates=sorted((ROOT/'.tools/ffmpeg').glob(f'*/bin/{name}.exe'))
    path=str(candidates[-1]) if candidates else shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} not installed; run python tools/bootstrap.py ffmpeg')
    return path

@contextmanager
def heavy_lock(directory=None):
    """Cross-process mutex shared by every Factory database and both renderers."""
    directory=Path(directory).resolve() if directory else ROOT/'data'
    if not directory.is_relative_to(ROOT):
        raise ValueError('Lock directory must be inside Factory')
    directory.mkdir(exist_ok=True)
    with (directory/'heavy.lock').open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size==0:
            lock.write(b'0')
            lock.flush()
        while True:
            try:
                lock.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except (OSError,BlockingIOError):
                time.sleep(.25)
        try:
            # A runner can die while its child is still alive. Do not overlap it.
            marker=directory/'heavy-process.json'
            if marker.exists():
                old=json.loads(marker.read_text())
                deadline=time.monotonic()+7200
                while psutil.pid_exists(old['pid']):
                    try:
                        if abs(psutil.Process(old['pid']).create_time()-old['created'])>.1:
                            break
                    except psutil.NoSuchProcess:
                        break
                    if time.monotonic()>deadline:
                        raise RuntimeError('HEAVY_PROCESS_RECONCILIATION_REQUIRED')
                    time.sleep(.5)
            yield
        finally:
            lock.seek(0)
            if os.name=='nt':
                msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(lock,fcntl.LOCK_UN)

def process(args, cwd: Path, log: Path, metrics: Path, timeout=7200):
    log.parent.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    peak=0
    with log.open('wb') as output:
        p=subprocess.Popen([str(a) for a in args],cwd=cwd,stdout=output,stderr=subprocess.STDOUT,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        proc=psutil.Process(p.pid)
        marker=ROOT/'data/heavy-process.json'
        marker.write_text(json.dumps({'pid':p.pid,'created':proc.create_time()}))
        try:
            while p.poll() is None:
                try:
                    tree=[proc]+proc.children(recursive=True)
                    peak=max(peak,sum(x.memory_info().rss for x in tree if x.is_running()))
                except (psutil.NoSuchProcess,psutil.AccessDenied):
                    pass
                if time.monotonic()-start>timeout:
                    for child in proc.children(recursive=True):
                        child.kill()
                    p.kill()
                    p.wait()
                    raise RuntimeError('RENDER_TIMEOUT')
                time.sleep(.25)
        finally:
            if p.poll() is not None and marker.exists():
                marker.unlink()
    record={'command':str(args[0]),'elapsed_seconds':round(time.monotonic()-start,2),'peak_tree_rss_bytes':peak,'exit_code':p.returncode,'log':str(log)}
    with metrics.open('a',encoding='utf-8') as out:
        out.write(json.dumps(record)+'\n')
    if p.returncode:
        tail=log.read_text(encoding='utf-8',errors='replace')[-1800:]
        raise RuntimeError(f'RENDER_FAILED ({p.returncode}): {tail}')
    return record

def probe(path: Path, config: Config, expected=None, strict=True, pixel_format=None):
    if not path.is_file() or path.stat().st_size==0:
        raise RuntimeError('EMPTY_MEDIA')
    args=[executable('ffprobe',config.ffprobe),'-v','error','-show_entries','format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt','-of','json',str(path)]
    result=subprocess.run(args,capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    info=json.loads(result.stdout)
    streams=[s for s in info['streams'] if s['codec_type']=='video']
    if not streams:
        raise RuntimeError('VIDEO_STREAM_MISSING')
    s=streams[0]
    if strict and (s['width'],s['height'],s['r_frame_rate'],s['codec_name']) != (1080,1920,'30/1','h264'):
        raise RuntimeError('INVALID_VIDEO_FORMAT')
    if pixel_format and s.get('pix_fmt')!=pixel_format:
        raise RuntimeError('INVALID_FINAL_PIXEL_FORMAT')
    duration=float(info['format']['duration'])
    if duration<=0:
        raise RuntimeError('INVALID_VIDEO_DURATION')
    if expected is not None and abs(duration-expected)>.08:
        raise RuntimeError('INVALID_VIDEO_DURATION')
    return info

class Remotion:
    def __init__(self,config: Config):
        self.config=config

    def render(self,case_id,photos,work):
        with heavy_lock():
            project=ROOT/'Remotion'
            target=project/'public/factory'/case_id
            target.mkdir(parents=True,exist_ok=True)
            cfg=json.loads((project/'cases/CASE_001.json').read_text(encoding='utf-8'))
            cfg.update(case_id=case_id,duration=24)
            cfg['photos']={}
            for key,p in photos.items():
                dest=target/(key+p.suffix)
                if dest.exists() and dest.read_bytes()!=p.read_bytes():
                    raise RuntimeError('IMMUTABLE_REMOTION_INPUT_CONFLICT')
                if not dest.exists():
                    shutil.copyfile(p,dest)
                cfg['photos'][key]=dest.relative_to(project/'public').as_posix()
            config_path=project/'cases/factory'/f'{case_id}.json'
            config_path.parent.mkdir(parents=True,exist_ok=True)
            if config_path.exists():
                frozen=json.loads(config_path.read_text(encoding='utf-8'))
                if frozen.get('photos')!=cfg['photos'] or frozen.get('case_id')!=case_id or frozen.get('duration')!=24 or frozen.get('fps')!=30:
                    raise RuntimeError('IMMUTABLE_REMOTION_CASE_CONFLICT')
            else:
                config_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
            work.mkdir(parents=True,exist_ok=True)
            output,meta=work/'screencast.mp4',work/'timeline.json'
            process(['node','tools/render-case.mjs',str(config_path),'--output',str(output),'--metadata',str(meta),'--restore-config'],project,work/'remotion.log',self.config.data/'logs/performance.jsonl')
            probe(output,self.config,24)
            return output,json.loads(meta.read_text())

def ass_time(t):
    centis=round(t*100)
    return f'{centis//360000}:{centis//6000%60:02d}:{centis//100%60:02d}.{centis%100:02d}'

def ass_text(text):
    return text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n','\\N')

class Composer:
    def __init__(self,config: Config):
        self.config=config

    def doctor(self):
        result=subprocess.run([executable('ffmpeg',self.config.ffmpeg),'-hide_banner','-filters'],capture_output=True,check=True)
        text=result.stdout.decode('utf-8',errors='replace')
        for name in ('subtitles','overlay','concat','fps','trim','setpts','pad'):
            if not any(line.split()[1:2]==[name] for line in text.splitlines()):
                raise RuntimeError(f'FFMPEG_FILTER_MISSING: {name}; use full portable build')

    def compose(self,screencast,avatar,hook,timeline,work):
        with heavy_lock():
            self.doctor()
            work.mkdir(parents=True,exist_ok=True)
            header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial,62,&H00FFFFFF,&H00FFFFFF,&H80000000,&H80000000,1,0,0,0,100,100,0,0,3,14,0,5,90,170,140,1
Style: Explain,Arial,42,&H00FFFFFF,&H00FFFFFF,&H80000000,&H80000000,1,0,0,0,100,100,0,0,3,8,0,8,90,170,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
            captions=[(0,3,'Main',hook),(27,30,'Main','Попробуй @vibecopy_bot')]
            labels={'galleryOriginal':'1. Выбери своё фото','galleryReference':'2. Добавь референс','processing':'3. Дождись обработки','result':'Готовый результат'}
            for event,text in labels.items():
                stage=timeline.get('stages',{}).get(event)
                if stage:
                    start=3+stage['start']/30
                    end=min(27,3+stage['end']/30,start+1.8)
                    captions.append((start,end,'Explain',text))
            (work/'captions.ass').write_text(header+''.join(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{ass_text(text)}\n' for a,b,style,text in captions),encoding='utf-8-sig')
            (work/'captions.json').write_text(json.dumps(captions,ensure_ascii=False),encoding='utf-8')
            filters=("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,split=2[av0][av1];"
                     "[av0]trim=duration=3,setpts=PTS-STARTPTS[a];[av1]trim=duration=3,setpts=PTS-STARTPTS[z];"
                     "[1:v]trim=duration=24,setpts=PTS-STARTPTS,fps=30,setsar=1[b];"
                     "[a][b][z]concat=n=3:v=1:a=0,subtitles=filename=captions.ass,scale=iw:ih:out_range=tv:out_color_matrix=bt709,format=yuv420p,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]")
            output=work/'master.mp4'
            process([executable('ffmpeg',self.config.ffmpeg),'-hide_banner','-y','-stream_loop','-1','-i',avatar,'-i',screencast,'-filter_complex_threads','1','-filter_complex',filters,'-map','[v]','-an','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-t','30','-movflags','+faststart',output],work,work/'ffmpeg.log',self.config.data/'logs/performance.jsonl')
            probe(output,self.config,30,pixel_format='yuv420p')
            return output
