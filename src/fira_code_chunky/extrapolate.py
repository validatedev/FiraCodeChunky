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


# Glyphs stores the display advance of zero-width combining marks in this lib
# key while writing width=0 to the GLIF. The synthetic Bold has no per-glyph
# lib of its own, so carry it through extrapolation; features.py reads it back
# to restore the spacing overlays' 1200 advance (F1/F2).
ORIGINAL_WIDTH_KEY = "com.schriftgestaltung.Glyphs.originalWidth"


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
    _extrapolate_hint_lists(light, bold, out, t)
    for attr in ("ascender", "descender", "capHeight", "xHeight", "italicAngle"):
        lv, bv = getattr(light.info, attr), getattr(bold.info, attr)
        if lv is not None and bv is not None:
            setattr(out.info, attr, round(_lerp(lv, bv, t)))
    for name in sorted(light.keys()):
        lg, bg = light[name], bold[name]
        og = out.newGlyph(name)
        og.width = round(_lerp(lg.width, bg.width, t))
        og.unicodes = list(lg.unicodes)
        if ORIGINAL_WIDTH_KEY in lg.lib:
            og.lib[ORIGINAL_WIDTH_KEY] = lg.lib[ORIGINAL_WIDTH_KEY]
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
    # Master lib keys the synthetic Bold must share with its interpolated
    # siblings (which inherit them from Instantiator). skipExportGlyphs keeps
    # build parts out of the binary and postscriptNames restores uniXXXX names
    # (F6); glyphOrder pins a stable order; the ufo2ft featureWriters/filters
    # keys make Bold compile with the same feature writers as the masters. The
    # master-specific keys (weightValue, fontMasterID/Order, weight) are
    # deliberately NOT copied.
    for key in (
        "public.skipExportGlyphs",
        "public.postscriptNames",
        "public.glyphOrder",
        "com.github.googlei18n.ufo2ft.featureWriters",
        "com.github.googlei18n.ufo2ft.filters",
    ):
        if key in light.lib:
            value = light.lib[key]
            out.lib[key] = list(value) if isinstance(value, list) else dict(value)
    return out


# OFL-required and identity records that live on font.info rather than being
# recomputed per-instance. The synthetic Bold has no upstream instance of its
# own, so these must be lifted verbatim from the light master.
#
# The family keeps several fields *constant* across weights (both masters carry
# identical values), so they are copied, not extrapolated:
#   - openTypeOS2Type=[] -> installable embedding (F5); missing it shipped
#     fsType=4 (Restricted License) on the Bold only.
#   - underline/strikeout geometry (F4) is identical on every weight upstream;
#     extrapolating it produced the -146/98, 638/98 Bold outlier.
#   - openTypeOS2Selection=[7] carries USE_TYPO_METRICS (F7) so Bold resolves
#     line height like its siblings.
#   - designer/manufacturer names + URLs (F7, name IDs 8/9/11/12).
#   - openTypeHeadCreated pins a stable creation date.
#   - postscriptIsFixedPitch + BlueFuzz/BlueScale/BlueShift are non-scaling CFF
#     hint parameters (F8); the scaling blue zones/stems are extrapolated below.
_OFL_INFO_ATTRS = (
    "copyright",
    "trademark",
    "openTypeNameLicense",
    "openTypeNameLicenseURL",
    "versionMajor",
    "versionMinor",
    "openTypeNameVersion",
    "openTypeOS2VendorID",
    "openTypeOS2Type",
    "openTypeOS2Selection",
    # PANOSE is a family-constant classification; keep the source value
    # [2,11,8,9,5,0,0,2,0,4] on the Bold rather than the all-zeros the binary
    # shipped. Google Fonts requires panose[1]=2/panose[4]=9 for monospace, and
    # official Bold's all-zeros is upstream's own inconsistency (do not copy it).
    "openTypeOS2Panose",
    "postscriptUnderlinePosition",
    "postscriptUnderlineThickness",
    "openTypeOS2StrikeoutPosition",
    "openTypeOS2StrikeoutSize",
    "openTypeNameDesigner",
    "openTypeNameDesignerURL",
    "openTypeNameManufacturer",
    "openTypeNameManufacturerURL",
    "openTypeHeadCreated",
    "postscriptIsFixedPitch",
    "postscriptBlueFuzz",
    "postscriptBlueScale",
    "postscriptBlueShift",
)

# CFF blue zones and standard stem widths genuinely scale with weight, so they
# are interpolated element-wise at the same t as the outlines (F8). Missing
# them, the Bold OTF shipped with no BlueValues/StdHW/StdVW and hinted poorly.
_HINT_LIST_ATTRS = (
    "postscriptBlueValues",
    "postscriptOtherBlues",
    "postscriptStemSnapH",
    "postscriptStemSnapV",
)


def _copy_info(src: ufoLib2.Font, dst: ufoLib2.Font) -> None:
    dst.info.familyName = src.info.familyName
    dst.info.styleName = src.info.styleName
    dst.info.unitsPerEm = src.info.unitsPerEm
    for attr in _OFL_INFO_ATTRS:
        value = getattr(src.info, attr)
        if value is not None:
            setattr(dst.info, attr, value)


def _extrapolate_hint_lists(
    light: ufoLib2.Font, bold: ufoLib2.Font, out: ufoLib2.Font, t: float
) -> None:
    for attr in _HINT_LIST_ATTRS:
        lv, bv = getattr(light.info, attr), getattr(bold.info, attr)
        if lv is not None and bv is not None:
            _check(len(lv) == len(bv), f"{attr}: master pair counts differ")
            result = [round(_lerp(a, b, t)) for a, b in zip(lv, bv, strict=True)]
            # Blue zones and stem arrays must stay strictly increasing: this
            # guards against a zone overlap or unsorted stems after
            # extrapolation (a single value is trivially ordered).
            _check(
                stem_widths_monotonic(result),
                f"{attr}: not strictly increasing after extrapolation: {result}",
            )
            setattr(out.info, attr, result)


def stem_widths_monotonic(widths: Sequence[float]) -> bool:
    return all(a < b for a, b in pairwise(widths))
