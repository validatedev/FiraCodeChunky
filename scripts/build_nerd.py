#!/usr/bin/env python3
"""Patch Fira Code Chunky static TTFs into Nerd Font Mono variants.

Requires:
  - ``dist/ttf/FiraCodeChunky-*.ttf`` (from ``uv run chunky-build``)
  - ``build/nerd-fonts/font-patcher`` (from ``./scripts/fetch_nerd_fonts.sh``)
  - FontForge with Python bindings on PATH (``fontforge`` CLI)

On macOS, if fontforge is missing: ``brew install fontforge``.

Usage:
    uv run python scripts/build_nerd.py

Writes ``dist/nerd/FiraCodeChunkyNerdFontMono-*.ttf`` for each static weight.

Naming: font-patcher with ``--complete --mono --makegroups 1`` produces
family ``FiraCodeChunky Nerd Font Mono`` and files like
``FiraCodeChunkyNerdFontMono-Regular.ttf``. Weight metadata
(usWeightClass 300/400/500/600/700) is left intact by the patcher.

Variable font: intentionally skipped. font-patcher does not cleanly preserve
VF axes/instances for this family (see README and the nerd-font report);
only the five statics are patched.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_TTF = ROOT / "dist" / "ttf"
DIST_NERD = ROOT / "dist" / "nerd"
PATCHER = ROOT / "build" / "nerd-fonts" / "font-patcher"

STYLES = ("Light", "Regular", "Medium", "SemiBold", "Bold")

# Official nerd-fonts flags: complete glyph sets, single-width icons (Mono).
# --makegroups 1: modern naming (Family + "Nerd Font Mono" + style).
PATCHER_FLAGS = (
    "--complete",
    "--mono",
    "--makegroups",
    "1",
    "--quiet",
)


def find_fontforge() -> str | None:
    """Return a fontforge executable path, or None if unavailable."""
    path = shutil.which("fontforge")
    if path:
        return path
    # Homebrew python bindings alone are not enough; the CLI runs the script.
    return None


def source_fonts() -> list[Path]:
    fonts = [DIST_TTF / f"FiraCodeChunky-{style}.ttf" for style in STYLES]
    return fonts


def patch_one(fontforge: str, src: Path, out_dir: Path) -> Path:
    """Run font-patcher on one static TTF; return the produced path."""
    cmd = [
        fontforge,
        "-script",
        str(PATCHER),
        *PATCHER_FLAGS,
        "--outputdir",
        str(out_dir),
        str(src),
    ]
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)

    # font-patcher names output from the SFNT family; with --mono + makegroups 1
    # the stem is FiraCodeChunkyNerdFontMono-<Style>.ttf
    style = src.stem.removeprefix("FiraCodeChunky-")
    expected = out_dir / f"FiraCodeChunkyNerdFontMono-{style}.ttf"
    if expected.exists():
        return expected

    # Fallback: any new Mono ttf for this style (handles patcher renames).
    candidates = sorted(out_dir.glob(f"*NerdFontMono*-{style}.ttf"))
    if not candidates:
        candidates = sorted(out_dir.glob(f"*{style}.ttf"))
    if not candidates:
        raise FileNotFoundError(
            f"font-patcher did not produce an output for {src.name} in {out_dir}"
        )
    return candidates[0]


def main() -> int:
    if not PATCHER.exists():
        print(
            f"missing {PATCHER}; run ./scripts/fetch_nerd_fonts.sh first",
            file=sys.stderr,
        )
        return 1

    fonts = source_fonts()
    missing = [p for p in fonts if not p.exists()]
    if missing:
        print("missing source TTFs (run `uv run chunky-build` first):", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    fontforge = find_fontforge()
    if fontforge is None:
        print(
            "fontforge not found on PATH.\n"
            "Nerd Font patching requires FontForge with Python bindings.\n"
            "  macOS:  brew install fontforge\n"
            "  Debian/Ubuntu: sudo apt install fontforge python3-fontforge\n"
            "fontforge is not installable via uv/PyPI.",
            file=sys.stderr,
        )
        return 1

    DIST_NERD.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for src in fonts:
        out = patch_one(fontforge, src, DIST_NERD)
        produced.append(out)
        print(f"wrote {out.relative_to(ROOT)}", flush=True)

    print(f"patched {len(produced)} fonts into {DIST_NERD.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
