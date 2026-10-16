import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from .config import Config, ROOT
from .engine import Factory
from .worker import Contract
from .media import Composer, executable

def main():
    parser=argparse.ArgumentParser(description='Vibe Copy Content Factory — local reviewed video production')
    parser.add_argument('--data',type=Path,help='Data directory inside this project')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('doctor','init','status','run','bot'):
        commands.add_parser(name)
    imp=commands.add_parser('import-library');imp.add_argument('manifest',type=Path)
    fake=commands.add_parser('fake-worker');fake.add_argument('--port',type=int,default=8765)
    review=commands.add_parser('review');review.add_argument('kind',choices=['case','video']);review.add_argument('id');review.add_argument('action');review.add_argument('--attempt',type=int)
    start=commands.add_parser('start');start.add_argument('mode',choices=['a','b'])
    retry=commands.add_parser('resume');retry.add_argument('job_id')
    dem=commands.add_parser('demo');dem.add_argument('--resume',type=Path);dem.add_argument('--verify-remotion',action='store_true')
    args=parser.parse_args()
    if args.command=='demo':
        from .demo import demo
        asyncio.run(demo(args.resume,args.verify_remotion))
        return
    config=Config.load()
    if args.data:
        config.data=args.data.resolve()
        config.__post_init__()
    if args.command=='doctor':
        Contract();Composer(config).doctor()
        node=subprocess.run(['node','--version'],capture_output=True,check=True).stdout.decode().strip()
        print(json.dumps({'mode':config.mode,'python':sys.version.split()[0],'node':node,'ffmpeg':executable('ffmpeg',config.ffmpeg),'ffprobe':executable('ffprobe',config.ffprobe),'contract':'1.0 / SHA256 OK','real_integrations':'UNVERIFIED'},indent=2))
        return
    factory=Factory(config)
    if args.command=='init':
        print('Initialized '+str(config.data)+' · '+config.mode)
    elif args.command=='import-library':
        print('Imported pairs:',factory.library.import_manifest(args.manifest))
    elif args.command=='status':
        print(json.dumps(factory.status(),ensure_ascii=False,indent=2))
    elif args.command=='review':
        print(factory.review_case(args.id,args.action,args.attempt) if args.kind=='case' else factory.review_video(args.id,args.action))
    elif args.command=='start':
        print(factory.start_a() if args.mode=='a' else factory.start_b())
    elif args.command=='resume':
        print(factory.resume(args.job_id))
    elif args.command=='run':
        asyncio.run(factory.run())
    elif args.command=='bot':
        from .bot import run_bot
        asyncio.run(run_bot(factory))
    elif args.command=='fake-worker':
        from aiohttp import web
        from .fake_worker import FakeWorker
        if config.mode!='MOCK':
            raise ValueError('Fake Worker requires MOCK mode')
        web.run_app(FakeWorker(config.data/'fake-worker.sqlite3',config.worker_token).app(),host='127.0.0.1',port=args.port)

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(type(e).__name__+': '+str(e),file=sys.stderr)
        sys.exit(1)
