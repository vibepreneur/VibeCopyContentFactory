from pathlib import Path
from io import BytesIO
import hashlib
import json
import mimetypes
import os
import time
from PIL import Image
from .config import ROOT
from .db import DB, uid

class Library:
    def __init__(self, db: DB, root: Path):
        self.db, self.root = db, root
        for folder in ("staging", "approved", "rejected", "logs", "work"):
            (root / folder).mkdir(parents=True, exist_ok=True)

    def add(self, content: bytes, kind: str, mime: str, status="PENDING", rights="unknown", source=None, metadata=None):
        digest = hashlib.sha256(content).hexdigest()
        existing = self.db.one("SELECT * FROM assets WHERE type=? AND sha256=?", (kind, digest))
        if existing:
            self.file(existing['id'])
            return existing['id']
        ext = {"image/jpeg":".jpg", "image/png":".png", "image/webp":".webp", "video/mp4":".mp4"}.get(mime)
        if not ext:
            raise ValueError("Unsupported asset MIME")
        width = height = None
        if mime.startswith("image/"):
            with Image.open(BytesIO(content)) as im:
                width, height = im.size
                im.verify()
        folder = "approved" if status == "APPROVED" else "staging"
        path = self.root / folder / kind / (digest + ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temp = path.with_suffix('.' + uid() + '.tmp')
            temp.write_bytes(content)
            os.replace(temp, path)
        asset_id = uid()
        with self.db.transaction() as c:
            c.execute("INSERT OR IGNORE INTO assets(id,type,path,sha256,mime,width,height,rights_status,approved_at,source_id,created_at,status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (asset_id,kind,str(path),digest,mime,width,height,rights,time.time() if status=='APPROVED' else None,source,time.time(),status,json.dumps(metadata or {})))
            return c.execute("SELECT id FROM assets WHERE type=? AND sha256=?", (kind,digest)).fetchone()[0]

    def file(self, asset_id):
        a = self.db.one("SELECT * FROM assets WHERE id=?", (asset_id,))
        if not a:
            raise ValueError("ASSET_NOT_FOUND")
        p = Path(a['path']).resolve()
        if not p.is_relative_to(self.root.resolve()) or not p.is_file():
            raise ValueError("ASSET_MISSING")
        if hashlib.sha256(p.read_bytes()).hexdigest() != a['sha256']:
            raise ValueError("ASSET_HASH_MISMATCH")
        return p

    def approve(self, asset_id):
        target = self.snapshot(asset_id)
        self.db.execute("UPDATE assets SET status='APPROVED',approved_at=?,path=? WHERE id=?", (time.time(),str(target),asset_id))

    def snapshot(self, asset_id):
        a = self.db.one("SELECT * FROM assets WHERE id=?", (asset_id,))
        p = self.file(asset_id)
        target = self.root / "approved" / a['type'] / p.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=a['sha256']:
                raise ValueError('APPROVED_SNAPSHOT_HASH_MISMATCH')
        else:
            temp=target.with_suffix('.'+uid()+'.tmp')
            temp.write_bytes(p.read_bytes())
            os.replace(temp,target)
        return target

    def import_manifest(self, manifest: Path):
        manifest = manifest.resolve()
        if not manifest.is_relative_to(ROOT):
            raise ValueError("Manifest must be inside project")
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        count = 0
        for pair in doc.get('pairs', []):
            ids = []
            for kind, key in (("original","original"),("reference","reference")):
                p = (manifest.parent / pair[key]).resolve()
                if not p.is_relative_to(ROOT) or not p.is_file():
                    raise ValueError("Invalid or missing import path")
                mime = mimetypes.guess_type(p.name)[0]
                ids.append(self.add(p.read_bytes(), kind, mime, "APPROVED", pair.get('rights_status','unknown')))
            with self.db.transaction() as c:
                existing = c.execute("SELECT * FROM photo_pairs WHERE id=?", (pair['id'],)).fetchone()
                if existing and (existing['original_asset_id'],existing['reference_asset_id']) != tuple(ids):
                    raise ValueError("PAIR_ID_CONFLICT")
                c.execute("INSERT OR IGNORE INTO photo_pairs VALUES(?,?,?,?,?)", (pair['id'],*ids,json.dumps(pair.get('tags',[])),"APPROVED"))
            count += 1
        for avatar in doc.get('avatars',[]):
            path=(manifest.parent/avatar['path']).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError('Invalid or missing avatar path')
            from .media import probe
            from .config import Config
            info=probe(path,Config(data=self.root),strict=False)
            status='APPROVED' if avatar.get('approved') is True else 'PENDING'
            asset=self.add(path.read_bytes(),'animated_avatar','video/mp4',status,avatar.get('rights_status','unknown'),metadata={'imported':True,'media':info})
            if status=='APPROVED':
                self.approve(asset)
        for hook in doc.get('hooks',[]):
            with self.db.transaction() as c:
                old=c.execute('SELECT text FROM hooks WHERE id=?',(hook['id'],)).fetchone()
                if old and old['text']!=hook['text']:
                    raise ValueError('HOOK_ID_CONFLICT')
                c.execute('INSERT OR IGNORE INTO hooks VALUES(?,?,?,?)',(hook['id'],hook['text'],json.dumps(hook.get('tags',[])),'APPROVED' if hook.get('approved') is True else 'PENDING'))
        return count
