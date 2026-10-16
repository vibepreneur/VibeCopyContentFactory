from dataclasses import dataclass, field
from pathlib import Path
import os
import math
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class Config:
    data: Path = field(default_factory=lambda: ROOT / "data/local")
    mode: str = "MOCK"
    worker_url: str = "http://127.0.0.1:8765"
    worker_token: str = "factory-local-fake-token"
    admin_ids: tuple[int, ...] = ()
    telegram_token: str = ""
    max_retries: int = 3
    budget: float = 0
    attempt_cap: float = 0
    allow_paid: bool = False
    ffmpeg: str = ""
    ffprobe: str = ""

    def __post_init__(self):
        self.data = self.data.resolve()
        if not self.data.is_relative_to(ROOT):
            raise ValueError("Factory data must be inside this project")
        if self.mode not in ("MOCK", "REAL"):
            raise ValueError("FACTORY_MODE must be MOCK or REAL")
        if self.max_retries<0:
            raise ValueError('FACTORY_MAX_RETRIES must be nonnegative')
        if not all(math.isfinite(v) and v>=0 for v in (self.budget,self.attempt_cap)):
            raise ValueError('Spending caps must be finite and nonnegative')

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            data=Path(os.getenv("FACTORY_DATA_DIR", str(ROOT / "data/local"))),
            mode=os.getenv("FACTORY_MODE", "MOCK"),
            worker_url=os.getenv("WORKER_BASE_URL", "http://127.0.0.1:8765"),
            worker_token=os.getenv("WORKER_BEARER_TOKEN", "factory-local-fake-token"),
            admin_ids=tuple(int(v.strip()) for v in os.getenv("FACTORY_ADMIN_USER_IDS", "").split(",") if v.strip()),
            telegram_token=os.getenv("FACTORY_TELEGRAM_TOKEN", ""),
            max_retries=int(os.getenv("FACTORY_MAX_RETRIES", "3")),
            budget=float(os.getenv("FACTORY_BATCH_BUDGET", "0")),
            attempt_cap=float(os.getenv("FACTORY_ATTEMPT_CAP", "0")),
            allow_paid=os.getenv("FACTORY_ALLOW_PAID_CALLS", "false").lower() == "true",
            ffmpeg=os.getenv("FACTORY_FFMPEG", ""),
            ffprobe=os.getenv("FACTORY_FFPROBE", ""),
        )
