from io import BytesIO
from pathlib import Path
import json
import pytest
from PIL import Image
from factory.config import ROOT, Config
from factory.db import uid
from factory.engine import Factory

@pytest.fixture
def workspace():
    path=ROOT/'.cache/tests'/uid()
    path.mkdir(parents=True)
    return path

def picture(color):
    out=BytesIO()
    Image.new('RGB',(64,96),color).save(out,format='PNG')
    return out.getvalue()

def seed(factory,count=10):
    root=factory.config.data/'imports'
    root.mkdir(parents=True,exist_ok=True)
    pairs=[]
    for n in range(count):
        original,ref=root/f'o{n}.png',root/f'r{n}.png'
        original.write_bytes(picture((n*19%255,40,160)))
        ref.write_bytes(picture((30,n*23%255,90)))
        pairs.append({'id':f'pair-{n:02d}','original':original.name,'reference':ref.name,'rights_status':'test-only'})
    manifest=root/'manifest.json'
    manifest.write_text(json.dumps({'pairs':pairs}))
    factory.library.import_manifest(manifest)
    factory.library.add(b'UNIT TEST VIDEO FIXTURE','animated_avatar','video/mp4','APPROVED','test-only')
    return manifest

@pytest.fixture
def factory(workspace):
    f=Factory(Config(data=workspace,admin_ids=(42,)))
    seed(f)
    return f
