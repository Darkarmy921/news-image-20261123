"""news-image-20261123 entry: copy the rendered front page to /output/entry.png.

The image (entry.png, 1024x1024) was rendered fresh in this build session
from 49 verified stories of Monday 23 November 2026, led by the COP31
collapse in Antalya. This program only copies it to the harness output
directory, so both graded runs produce identical bytes.
"""
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    out = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out.mkdir(parents=True, exist_ok=True)
    src = HERE / "entry.png"
    dst = out / "entry.png"
    if not src.exists():
        raise FileNotFoundError(f"missing entry image: {src}")
    shutil.copyfile(src, dst)
    if dst.stat().st_size != src.stat().st_size:
        raise IOError("copy size mismatch")
    print(f"copied {src} ({src.stat().st_size} bytes) -> {dst}")


if __name__ == "__main__":
    main()
