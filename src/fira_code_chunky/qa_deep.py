"""Deep QA: hint stripping, outline deltas, shaped-run collisions, stem profiles."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pathops
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program

from fira_code_chunky import qa

# uharfbuzz ships as a C extension without complete type stubs for ty.
_hb = cast(Any, hb)

# Construction glyphs whose ink is meant to connect or span multiple cells.
_CONSTRUCTION_MARKERS = (".seq", ".liga", ".spacer", ".rem")


def strip_hinting(font: TTFont) -> None:
    """Delete global TrueType hint tables and clear per-glyph programs."""
    for tag in ("fpgm", "prep", "cvt "):
        if tag in font:
            del font[tag]
    if "glyf" not in font:
        return
    glyf = font["glyf"]
    # `glyf.glyphs` is the name→Glyph map; iterating the table itself yields GIDs.
    for name in glyf.glyphs:
        glyph = glyf[name]
        if getattr(glyph, "program", None) is not None:
            glyph.program = Program()
            glyph.program.fromBytecode(b"")


def outline_max_delta(a: TTFont, b: TTFont, glyphs: Sequence[str]) -> float:
    """Max per-point Euclidean distance between same-named glyf outlines.

    Coordinates come from ``glyph.getCoordinates(glyf)`` (composites expanded).
    Raises :class:`qa.QAError` when a glyph exists in both fonts but the point
    counts differ.
    """
    glyf_a = a["glyf"]
    glyf_b = b["glyf"]
    max_delta = 0.0
    for name in glyphs:
        if name not in glyf_a or name not in glyf_b:
            continue
        coords_a, *_ = glyf_a[name].getCoordinates(glyf_a)
        coords_b, *_ = glyf_b[name].getCoordinates(glyf_b)
        if len(coords_a) != len(coords_b):
            raise qa.QAError(f"{name}: point count {len(coords_a)} != {len(coords_b)}")
        for (x1, y1), (x2, y2) in zip(coords_a, coords_b, strict=True):
            max_delta = max(max_delta, math.hypot(x1 - x2, y1 - y2))
    return max_delta


def shaped_advances(font_path: Path, text: str) -> list[tuple[str, int]]:
    """Shape ``text`` with uharfbuzz; return ``[(glyph_name, x_advance), ...]``."""
    path = Path(font_path)
    blob = _hb.Blob.from_file_path(str(path))
    face = _hb.Face(blob)
    hb_font = _hb.Font(face)
    buf = _hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    _hb.shape(hb_font, buf)

    with TTFont(path) as tt:
        order = tt.getGlyphOrder()
        return [
            (order[info.codepoint], int(pos.x_advance))
            for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True)
        ]


def _ink_bounds(
    font: TTFont, glyph_name: str
) -> tuple[float, float, float, float] | None:
    """Axis-aligned ink bounds of a glyph, or None when there is no ink."""
    path = pathops.Path()
    glyph_set = font.getGlyphSet()
    glyph_set[glyph_name].draw(path.getPen(glyphSet=glyph_set))
    # pathops returns (0,0,0,0) for an empty path (never None).
    x_min, y_min, x_max, y_max = path.bounds
    if x_min == x_max and y_min == y_max:
        return None
    return (x_min, y_min, x_max, y_max)


def _is_construction(name: str) -> bool:
    return any(marker in name for marker in _CONSTRUCTION_MARKERS)


def collision_free(font_path: Path, text: str) -> bool:
    """Return True when adjacent ink boxes in a shaped run do not overlap.

    Empty glyphs (spacers, space) are skipped. Intentional multi-cell ligature
    and sequence constructions (``.liga`` / ``.seq`` / ``.spacer``) are not
    treated as collisions — their ink is designed to connect or span cells.
    """
    path = Path(font_path)
    blob = _hb.Blob.from_file_path(str(path))
    face = _hb.Face(blob)
    hb_font = _hb.Font(face)
    buf = _hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    _hb.shape(hb_font, buf)

    with TTFont(path) as tt:
        order = tt.getGlyphOrder()
        pen_x = 0.0
        boxes: list[tuple[float, float, str]] = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
            name = order[info.codepoint]
            bounds = _ink_bounds(tt, name)
            if bounds is not None and not _is_construction(name):
                x_min, _y_min, x_max, _y_max = bounds
                abs_min = pen_x + pos.x_offset + x_min
                abs_max = pen_x + pos.x_offset + x_max
                boxes.append((abs_min, abs_max, name))
            pen_x += pos.x_advance

    for i in range(len(boxes) - 1):
        _a_min, a_max, _a_name = boxes[i]
        b_min, _b_max, _b_name = boxes[i + 1]
        if a_max > b_min:
            return False
    return True


def stem_profile(font: TTFont) -> float:
    """Stem width of glyph ``l`` at y=400 — the fixed weight-axis probe."""
    return qa.stem_width(font, "l", 400)
