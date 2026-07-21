"""Linear two-master extrapolation for the design-750 Bold.

fontTools' VariationModel defaults to extrapolate=False and varLib.instancer
cannot exceed the fvar range, so the 750 master is baked with explicit linear
math: value = light + t * (bold - light), with t computed from the master
design locations (109/96 on the real upstream axis map; 1.125 on the linear
micro fixture).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

import ufoLib2


class IncompatibleMastersError(ValueError):
    pass


def design_t(coord: float, lo: float = 300, hi: float = 700) -> float:
    return (coord - lo) / (hi - lo)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise IncompatibleMastersError(msg)


def extrapolate_font(light: ufoLib2.Font, bold: ufoLib2.Font, t: float) -> ufoLib2.Font:
    _check(sorted(light.keys()) == sorted(bold.keys()), "glyph sets differ")
    out = ufoLib2.Font()
    _copy_info(light, out)
    for attr in ("ascender", "descender", "capHeight", "xHeight", "italicAngle"):
        lv, bv = getattr(light.info, attr), getattr(bold.info, attr)
        if lv is not None and bv is not None:
            setattr(out.info, attr, round(_lerp(lv, bv, t)))
    for name in sorted(light.keys()):
        lg, bg = light[name], bold[name]
        og = out.newGlyph(name)
        og.width = round(_lerp(lg.width, bg.width, t))
        og.unicodes = list(lg.unicodes)
        _check(len(lg.contours) == len(bg.contours), f"{name}: contour count differs")
        pen = og.getPointPen()
        for lc, bc in zip(lg.contours, bg.contours, strict=True):
            _check(len(lc.points) == len(bc.points), f"{name}: point count differs")
            pen.beginPath()
            for lp, bp in zip(lc.points, bc.points, strict=True):
                pen.addPoint(
                    (round(_lerp(lp.x, bp.x, t)), round(_lerp(lp.y, bp.y, t))),
                    segmentType=lp.type,
                    smooth=lp.smooth,
                )
            pen.endPath()
        _check(
            len(lg.components) == len(bg.components), f"{name}: component count differs"
        )
        for lcomp, bcomp in zip(lg.components, bg.components, strict=True):
            _check(
                lcomp.baseGlyph == bcomp.baseGlyph, f"{name}: component base differs"
            )
            lt, bt = lcomp.transformation, bcomp.transformation
            og.components.append(
                ufoLib2.objects.Component(
                    baseGlyph=lcomp.baseGlyph,
                    transformation=tuple(
                        round(_lerp(a, b, t)) if i >= 4 else _lerp(a, b, t)
                        for i, (a, b) in enumerate(zip(lt, bt, strict=True))
                    ),
                )
            )
        _check(len(lg.anchors) == len(bg.anchors), f"{name}: anchor count differs")
        for la, ba in zip(lg.anchors, bg.anchors, strict=True):
            og.appendAnchor(
                {
                    "name": la.name,
                    "x": round(_lerp(la.x, ba.x, t)),
                    "y": round(_lerp(la.y, ba.y, t)),
                }
            )
    pairs = set(light.kerning) | set(bold.kerning)
    for pair in pairs:
        out.kerning[pair] = round(
            _lerp(light.kerning.get(pair, 0), bold.kerning.get(pair, 0), t)
        )
    out.features.text = light.features.text
    out.groups.update(light.groups)
    return out


# OFL-required and identity records that live on font.info rather than being
# recomputed per-instance. The synthetic Bold has no upstream instance of its
# own, so these must be lifted verbatim from the light master (Fix 1).
_OFL_INFO_ATTRS = (
    "copyright",
    "trademark",
    "openTypeNameLicense",
    "openTypeNameLicenseURL",
    "versionMajor",
    "versionMinor",
    "openTypeNameVersion",
    "openTypeOS2VendorID",
)


def _copy_info(src: ufoLib2.Font, dst: ufoLib2.Font) -> None:
    dst.info.familyName = src.info.familyName
    dst.info.styleName = src.info.styleName
    dst.info.unitsPerEm = src.info.unitsPerEm
    for attr in _OFL_INFO_ATTRS:
        value = getattr(src.info, attr)
        if value is not None:
            setattr(dst.info, attr, value)


def stem_widths_monotonic(widths: Sequence[float]) -> bool:
    return all(a < b for a, b in pairwise(widths))
