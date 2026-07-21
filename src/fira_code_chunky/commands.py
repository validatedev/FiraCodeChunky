"""Pure argv builders for the font toolchain."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


def glyphs2ufo_command(glyphs: Path, master_dir: Path, designspace: Path) -> list[str]:
    return [
        "glyphs2ufo",
        str(glyphs),
        "-m",
        str(master_dir),
        "--designspace-path",
        str(designspace),
        "--write-public-skip-export-glyphs",
        # Default is --no-generate-GDEF (backward compat). Without categories,
        # ufo2ft mark writers treat spacing accents (grave, acute, …) that
        # carry _top anchors as GDEF marks; terminals then glue backticks onto
        # the previous letter. Match Glyphs export: write openTypeCategories.
        "--generate-GDEF",
    ]


def fontmake_ufo_command(
    ufo: Path, fmt: str, out_dir: Path, extra_flags: Sequence[str] = ()
) -> list[str]:
    if fmt not in {"ttf", "otf"}:
        raise ValueError(f"unsupported format: {fmt!r}")
    return [
        "fontmake",
        "-u",
        str(ufo),
        "-o",
        fmt,
        "--output-dir",
        str(out_dir),
        *extra_flags,
    ]


def fontmake_variable_command(
    designspace: Path, out_dir: Path, extra_flags: Sequence[str] = ()
) -> list[str]:
    return [
        "fontmake",
        "-m",
        str(designspace),
        "-o",
        "variable",
        "--output-dir",
        str(out_dir),
        *extra_flags,
    ]


def ttfautohint_command(src: Path, dest: Path) -> list[str]:
    # ttfautohint ships no standalone CLI here; ttfautohint-py bundles the real
    # binary and exposes it as ``python -m ttfautohint`` (a locked dependency,
    # so always present under the project interpreter).
    return [sys.executable, "-m", "ttfautohint", "--no-info", str(src), str(dest)]


def otfautohint_command(otf: Path) -> list[str]:
    return ["otfautohint", "--overwrite", str(otf)]


def gftools_fix_command(font: Path) -> list[str]:
    return ["gftools", "fix-font", "-o", str(font), str(font)]
