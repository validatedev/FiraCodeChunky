#!/usr/bin/env python3
"""Patch Fira Code Chunky static TTFs into the three stock Nerd Font variants.

Requires:
  - ``dist/ttf/FiraCodeChunky-*.ttf`` (from ``uv run chunky-build``)
  - ``build/nerd-fonts/font-patcher`` (from ``./scripts/fetch_nerd_fonts.sh``)
  - FontForge with Python bindings on PATH (``fontforge`` CLI)

On macOS, if fontforge is missing, run ``brew install fontforge``.

Usage:
    uv run python scripts/build_nerd.py

Writes, for each of the five static weights, three width variants into
``dist/nerd/``, matching what upstream Fira Code ships:

  - ``FiraCodeChunkyNerdFont-<Style>.ttf``      (plain, icons overhang the cell)
  - ``FiraCodeChunkyNerdFontMono-<Style>.ttf``  (--mono, every glyph one cell)
  - ``FiraCodeChunkyNerdFontPropo-<Style>.ttf`` (--variable-width-glyphs, proportional)

Naming. font-patcher with ``--makegroups 1`` derives the family/subfamily from
the source SFNT names and appends the variant tag, producing families
``FiraCodeChunky Nerd Font`` / ``... Mono`` / ``... Propo`` and the filenames
above. Weight metadata (usWeightClass 300/400/500/600/700) is left intact.

``post.isFixedPitch`` is *emergent*, not set by the patcher. Mono forces every
advance to one cell (FontForge computes isFixedPitch=1). Propo leaves
proportional, non-uniform advances (isFixedPitch=0). Plain keeps one-cell
ADVANCES too. Icons overhang only in the outline, not the advance width,
so for this clean-monospace source plain is ALSO isFixedPitch=1. Plain is
distinguished from Mono by icon-outline overhang, not by isFixedPitch.
(Upstream stock Fira Code's plain shows isFixedPitch=0 only because of one
non-monospace-width glyph absent from this source.) This is asserted in
tests/integration/test_nerd.py.

Variable font is intentionally skipped. font-patcher does not cleanly preserve
VF axes/instances for this family. Only the five statics are patched.
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

# Flags common to every variant: complete glyph sets, modern naming
# (--makegroups 1: Family + "Nerd Font[ Mono| Propo]" + style), quiet output.
# The per-variant width flag is kept OUT of this tuple on purpose: --mono and
# --variable-width-glyphs are contradictory, and with --quiet the patcher
# silently drops the loser, so a leaked --mono would mislabel Propo as Mono.
COMMON_FLAGS = ("--complete", "--makegroups", "1", "--quiet")

# (id, family, stem_infix, width_flags). stem_infix "" (plain) is intentionally
# empty. Never branch on its truthiness, doing so silently omits the plain variant.
VARIANTS = (
    ("plain", "FiraCodeChunky Nerd Font", "", ()),
    ("mono", "FiraCodeChunky Nerd Font Mono", "Mono", ("--mono",)),
    ("propo", "FiraCodeChunky Nerd Font Propo", "Propo", ("--variable-width-glyphs",)),
)


def find_fontforge() -> str | None:
    """Return a fontforge executable path, or None if unavailable."""
    path = shutil.which("fontforge")
    if path:
        return path
    # Homebrew python bindings alone are not enough, the CLI runs the script.
    return None


def source_fonts() -> list[Path]:
    fonts = [DIST_TTF / f"FiraCodeChunky-{style}.ttf" for style in STYLES]
    return fonts


def patcher_command(
    fontforge: str, src: Path, out_dir: Path, width_flags: tuple[str, ...]
) -> list[str]:
    """Build the font-patcher argv for one (source, variant).

    Returns a freshly constructed list every call so per-variant width flags
    never accumulate across invocations.
    """
    return [
        fontforge,
        "-script",
        str(PATCHER),
        *COMMON_FLAGS,
        *width_flags,
        "--outputdir",
        str(out_dir),
        str(src),
    ]


def patch_one(
    fontforge: str,
    src: Path,
    out_dir: Path,
    stem_infix: str,
    width_flags: tuple[str, ...],
) -> Path:
    """Run font-patcher on one static TTF for one variant, return its path.

    Resolves the output by its exact expected name. There is deliberately no
    glob fallback: the plain stem ``FiraCodeChunkyNerdFont-`` is a prefix of the
    Mono/Propo stems, so any wildcard would cross-match variants sharing
    ``dist/nerd/``. A missing exact name is a hard error, not a silent guess.
    """
    cmd = patcher_command(fontforge, src, out_dir, width_flags)
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)

    style = src.stem.removeprefix("FiraCodeChunky-")
    expected = out_dir / f"FiraCodeChunkyNerdFont{stem_infix}-{style}.ttf"
    if not expected.exists():
        raise FileNotFoundError(
            f"font-patcher did not produce {expected.name} for {src.name} in {out_dir}"
        )
    return expected


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
    # Wipe any pre-existing outputs so every file below provably comes from
    # THIS run: patch_one's exists() check only proves the patcher wrote
    # *a* file with the expected name, not that it wrote it just now, and a
    # dirty dist/nerd could otherwise hide a failed patch behind a stale file
    # (or leave stray extra fonts from a prior, differently-configured run).
    for stale in DIST_NERD.glob("*.ttf"):
        stale.unlink()
    produced: list[Path] = []
    for _vid, _family, stem_infix, width_flags in VARIANTS:
        for src in fonts:
            out = patch_one(fontforge, src, DIST_NERD, stem_infix, width_flags)
            produced.append(out)
            print(f"wrote {out.relative_to(ROOT)}", flush=True)

    print(f"patched {len(produced)} fonts into {DIST_NERD.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
