"""Local toolchain setup. Never touches another project or system settings."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def backup():
    dest = ROOT / "data/baseline"
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for folder in ("src", "tools", "cases", "public/assets", "out"):
        for source in (ROOT / "Remotion" / folder).rglob("*"):
            if source.is_file():
                rel = source.relative_to(ROOT)
                manifest[str(rel)] = hashlib.sha256(source.read_bytes()).hexdigest()
                if folder in ("src", "tools", "cases"):
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.copy2(source, target)
    path = dest / "manifest.json"
    if not path.exists():
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Baseline: {len(manifest)} files; {path}")

def ffmpeg():
    base = "https://www.gyan.dev/ffmpeg/builds/"
    target = ROOT / ".tools/ffmpeg"
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "release.zip"
    with urllib.request.urlopen(base + "ffmpeg-release-essentials.zip.sha256", timeout=60) as r:
        expected = r.read().decode().split()[0].lower()
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        print("Downloading portable FFmpeg release Essentials...", flush=True)
        urllib.request.urlretrieve(base + "ffmpeg-release-essentials.zip", archive)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError("FFmpeg download SHA256 mismatch")
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            resolved = (target / entry.filename).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise RuntimeError("Unsafe archive path")
        z.extractall(target)
    (target / "download.json").write_text(json.dumps({"source": base, "sha256": actual}, indent=2))
    print("FFmpeg verified:", next(target.rglob("ffmpeg.exe")))

if __name__ == "__main__":
    {"backup": backup, "ffmpeg": ffmpeg}[sys.argv[1]]()
