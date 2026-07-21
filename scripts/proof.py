#!/usr/bin/env python3
"""Raster proof sheet for Fira Code Chunky statics (uses hb-view when available).

Usage:
    uv run python scripts/proof.py

Writes ``build/proof.png`` (or per-style PNGs if ImageMagick ``convert`` is
absent and a single montage cannot be assembled). Not part of the unit suite.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "ttf"
OUT_DIR = ROOT / "build"
PROOF = OUT_DIR / "proof.png"
TEXT = "@ # & g e o 8 S W  <=>  ->  !=  ===  !=="
STYLES = ("Light", "Regular", "Medium", "SemiBold", "Bold")
# Coding sizes where dropout matters.
PX_SIZES = (10, 12, 14, 16)


def main() -> int:
    hb_view = shutil.which("hb-view")
    if hb_view is None:
        print(
            "hb-view not found; install harfbuzz tools or check dist fonts in an editor",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tiles: list[Path] = []
    for style in STYLES:
        font = DIST / f"FiraCodeChunky-{style}.ttf"
        if not font.exists():
            print(f"missing {font}", file=sys.stderr)
            return 1
        for px in PX_SIZES:
            tile = OUT_DIR / f"proof-{style}-{px}.png"
            subprocess.run(
                [
                    hb_view,
                    str(font),
                    TEXT,
                    f"--font-size={px}",
                    f"--output-file={tile}",
                    "--output-format=png",
                    "--margin=8",
                ],
                check=True,
            )
            tiles.append(tile)

    magick = shutil.which("magick")
    convert = shutil.which("convert")
    if magick:
        subprocess.run([magick, *map(str, tiles), "-append", str(PROOF)], check=True)
        print(f"wrote {PROOF} ({len(tiles)} tiles)")
    elif convert:
        subprocess.run([convert, *map(str, tiles), "-append", str(PROOF)], check=True)
        print(f"wrote {PROOF} ({len(tiles)} tiles)")
    else:
        # Fall back: keep the Regular 14px tile as the proof representative.
        rep = OUT_DIR / "proof-Regular-14.png"
        shutil.copy(rep, PROOF)
        print(f"wrote {PROOF} (single tile; install ImageMagick for full montage)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
