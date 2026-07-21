"""QA checks: metadata assertions, normalized TTX, geometry probes."""

from __future__ import annotations

import io
import re
from typing import Any, cast

import pathops
from fontTools.ttLib import TTFont

from fira_code_chunky import PS_FAMILY
from fira_code_chunky.metadata import FS_BOLD, FS_REGULAR, MAC_BOLD, RIBBI, WIN

VOLATILE = re.compile(r".*(checkSumAdjustment|modified value=|created value=).*\n")


class QAError(AssertionError):
    pass


def normalized_ttx(font: TTFont, tables: tuple[str, ...] = ("name", "OS/2")) -> str:
    buf = io.StringIO()
    # cast: fontTools' saveXML kwargs (XMLSavingOptions) type-check as required.
    cast(Any, font).saveXML(buf, tables=list(tables))
    return VOLATILE.sub("", buf.getvalue())


def _name(font: TTFont, nid: int) -> str | None:
    rec = font["name"].getName(nid, *WIN)
    return None if rec is None else rec.toUnicode()


def assert_static_metadata(
    font: TTFont, family: str, style: str, weight_class: int
) -> None:
    problems: list[str] = []
    os2 = cast(Any, font["OS/2"])
    if os2.usWeightClass != weight_class:
        problems.append(f"usWeightClass {os2.usWeightClass} != {weight_class}")
    if os2.usWidthClass != 5:
        problems.append(f"usWidthClass {os2.usWidthClass} != 5")
    post = cast(Any, font["post"])
    if post.isFixedPitch != 1:
        problems.append(f"isFixedPitch {post.isFixedPitch} != 1")
    ribbi = style in RIBBI
    expect_1 = family if ribbi else f"{family} {style}"
    expect_2 = style if ribbi else "Regular"
    checks = {
        1: expect_1,
        2: expect_2,
        6: f"{PS_FAMILY}-{style.replace(' ', '')}",
    }
    if not ribbi:
        checks |= {16: family, 17: style}
    for nid, expected in checks.items():
        actual = _name(font, nid)
        if actual != expected:
            problems.append(f"name {nid}: {actual!r} != {expected!r}")
    if ribbi and (_name(font, 16) is not None or _name(font, 17) is not None):
        problems.append("RIBBI style must not carry name 16/17")
    # OFL compliance (Fix 1 regression gate): copyright, license text, and
    # license URL must be present and non-empty on every static, including
    # the hand-extrapolated Bold, which used to ship without them.
    for nid in (0, 13, 14):
        if not _name(font, nid):
            problems.append(f"name {nid}: missing or empty")
    want_bold = style == "Bold"
    if bool(os2.fsSelection & FS_BOLD) != want_bold:
        problems.append("fsSelection BOLD bit wrong")
    if bool(os2.fsSelection & FS_REGULAR) == want_bold:
        problems.append("fsSelection REGULAR bit wrong")
    if bool(cast(Any, font["head"]).macStyle & MAC_BOLD) != want_bold:
        problems.append("macStyle bold bit wrong")
    if problems:
        raise QAError(f"{family} {style}: " + "; ".join(problems))


def _glyph_path(font: TTFont, glyph_name: str) -> pathops.Path:
    glyph_set = font.getGlyphSet()
    path = pathops.Path()
    glyph_set[glyph_name].draw(path.getPen(glyphSet=glyph_set))
    return path


def stem_width(font: TTFont, glyph_name: str, y: float) -> float:
    band = pathops.Path()
    pen = band.getPen()
    pen.moveTo((-10000, y - 1))
    pen.lineTo((20000, y - 1))
    pen.lineTo((20000, y + 1))
    pen.lineTo((-10000, y + 1))
    pen.closePath()
    ink = pathops.op(_glyph_path(font, glyph_name), band, pathops.PathOp.INTERSECTION)
    contours = list(ink.contours)
    if not contours:
        raise QAError(f"no ink at y={y} in {glyph_name}")
    bounds = min(contours, key=lambda c: c.bounds[0]).bounds
    return bounds[2] - bounds[0]


def glyph_has_overlap(font: TTFont, glyph_name: str) -> bool:
    path = _glyph_path(font, glyph_name)
    simplified = pathops.simplify(path, clockwise=path.clockwise)
    return abs(path.area - simplified.area) > 0.5


def has_calt(font: TTFont) -> bool:
    if "GSUB" not in font:
        return False
    features = font["GSUB"].table.FeatureList.FeatureRecord
    tags = [f.FeatureTag for f in features]
    return "calt" in tags
