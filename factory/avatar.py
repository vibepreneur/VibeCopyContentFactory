"""Avatar provider boundary. A local clip is never represented as Kling output."""
from typing import Protocol
from .config import Config
from .library import Library

class AvatarProvider(Protocol):
    async def animate(self, static_asset_id: str, request_id: str) -> str: ...

class CachedAvatarProvider:
    def __init__(self,library: Library):
        self.library=library

    async def animate(self,static_asset_id='',request_id=''):
        row=self.library.db.one("SELECT id FROM assets WHERE type='animated_avatar' AND status='APPROVED' ORDER BY created_at,id LIMIT 1")
        if not row:
            raise RuntimeError('APPROVED_AVATAR_CLIP_REQUIRED')
        self.library.file(row['id'])
        return row['id']

class KlingProvider:
    def __init__(self,config: Config):
        self.config=config

    async def animate(self,static_asset_id,request_id):
        if not self.config.allow_paid or self.config.budget<=0 or self.config.attempt_cap<=0:
            raise RuntimeError('PAID_CALLS_DISABLED')
        raise RuntimeError('LIVE_KLING_API_NOT_CONFIGURED: select API/model and approve spending first')
