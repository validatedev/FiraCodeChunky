import pytest

from fira_code_chunky.extrapolate import (
    IncompatibleMastersError,
    design_t,
    extrapolate_font,
    stem_widths_monotonic,
)


def test_design_t():
    assert design_t(450) == 0.375
    assert design_t(750) == 1.125
    assert design_t(300) == 0.0
    assert design_t(700) == 1.0


def test_extrapolated_750_exact_points(micro_masters):
    light, bold = micro_masters
    font = extrapolate_font(light, bold, design_t(750))
    xs = sorted({p.x for p in font["I"].contours[0].points})
    assert xs == [235, 365]  # 280 - 1.125*40 = 235; 320 + 1.125*40 = 365; stem 130
    assert font["I"].width == 600
    assert (
        font["I"].anchors[0].y == 722
    )  # 700 + 1.125*20 = 722.5 -> banker's round to 722
    assert font.kerning[("I", "O")] == -44  # -8 - 1.125*32
    comp = font["Iacute"].components[1]
    assert (
        comp.transformation[5] == 202
    )  # 180 + 1.125*20 = 202.5 -> banker's round to 202


def test_extrapolation_matches_interpolation_inside_range(micro_masters):
    light, bold = micro_masters
    font = extrapolate_font(light, bold, design_t(450))
    xs = sorted({p.x for p in font["I"].contours[0].points})
    assert xs == [265, 335]


def test_incompatible_masters_raise(micro_masters):
    light, bold = micro_masters
    del bold["O"]
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_incompatible_point_counts_raise(micro_masters):
    light, bold = micro_masters
    pen = bold["I"].getPen()
    pen.moveTo((0, 0))
    pen.lineTo((1, 1))
    pen.lineTo((1, 0))
    pen.closePath()
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_incompatible_contour_counts_raise(micro_masters):
    light, bold = micro_masters
    pen = bold["I"].getPen()
    pen.moveTo((0, 0))
    pen.lineTo((1, 1))
    pen.lineTo((1, 0))
    pen.closePath()
    # bold["I"] now has 2 contours vs light's 1 -> contour count differs
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_incompatible_component_counts_raise(micro_masters):
    light, bold = micro_masters
    bold["Iacute"].components.pop()
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_incompatible_component_base_raise(micro_masters):
    light, bold = micro_masters
    bold["Iacute"].components[0].baseGlyph = "O"
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_incompatible_anchor_counts_raise(micro_masters):
    light, bold = micro_masters
    bold["I"].anchors.clear()
    with pytest.raises(IncompatibleMastersError):
        extrapolate_font(light, bold, 1.125)


def test_fontinfo_none_attr_is_skipped(micro_masters):
    light, bold = micro_masters
    # italicAngle is None on both masters -> the interpolation branch is skipped
    assert light.info.italicAngle is None
    assert bold.info.italicAngle is None
    font = extrapolate_font(light, bold, design_t(750))
    assert font.info.italicAngle is None
    # a present numeric attr is still interpolated
    assert font.info.ascender is not None


def test_extrapolated_font_copies_ofl_metadata(micro_masters):
    # Fix 1 (OFL compliance): the extrapolated Bold must carry the same
    # copyright/license/version/vendor records as the other statics, which
    # all derive from the light master. Regression for the metadata loss
    # that left the Bold binary without name IDs 0/13/14.
    light, bold = micro_masters
    assert light.info.copyright  # sanity: fixture actually carries the field
    font = extrapolate_font(light, bold, design_t(750))
    assert font.info.copyright == light.info.copyright
    assert font.info.trademark == light.info.trademark
    assert font.info.openTypeNameLicense == light.info.openTypeNameLicense
    assert font.info.openTypeNameLicenseURL == light.info.openTypeNameLicenseURL
    assert font.info.versionMajor == light.info.versionMajor
    assert font.info.versionMinor == light.info.versionMinor
    assert font.info.openTypeOS2VendorID == light.info.openTypeOS2VendorID
    # openTypeNameVersion is unset on the fixture -> must stay unset, not
    # crash, exercising the "copy only when present" guard.
    assert light.info.openTypeNameVersion is None
    assert font.info.openTypeNameVersion is None


def test_extrapolated_font_copies_family_constant_metadata(micro_masters):
    # F4/F5/F7: fields the family keeps constant across weights are copied
    # verbatim from the light master (not extrapolated), so the synthetic Bold
    # inherits installable embedding, USE_TYPO_METRICS, constant underline/
    # strikeout geometry, and the designer/manufacturer name records.
    light, bold = micro_masters
    font = extrapolate_font(light, bold, design_t(750))
    assert font.info.openTypeOS2Type == light.info.openTypeOS2Type == []
    assert font.info.openTypeOS2Selection == light.info.openTypeOS2Selection == [7]
    assert font.info.postscriptUnderlinePosition == -100
    assert font.info.postscriptUnderlineThickness == 50
    assert font.info.openTypeOS2StrikeoutPosition == 318
    assert font.info.openTypeOS2StrikeoutSize == 50
    assert font.info.openTypeNameDesigner == light.info.openTypeNameDesigner
    assert font.info.openTypeNameDesignerURL == light.info.openTypeNameDesignerURL
    assert font.info.openTypeNameManufacturer == light.info.openTypeNameManufacturer
    assert (
        font.info.openTypeNameManufacturerURL == light.info.openTypeNameManufacturerURL
    )


def test_extrapolated_font_interpolates_cff_hint_lists(micro_masters):
    # F8: blue zones and standard stems scale with weight, so they are
    # interpolated element-wise at the same t as the outlines (not copied).
    light, bold = micro_masters
    light.info.postscriptBlueValues = [-20, 0, 700, 720]
    bold.info.postscriptBlueValues = [-40, 0, 720, 760]
    light.info.postscriptStemSnapH = [40]
    bold.info.postscriptStemSnapH = [120]
    light.info.postscriptStemSnapV = [50]
    bold.info.postscriptStemSnapV = [130]
    light.info.postscriptOtherBlues = [-200, -180]
    bold.info.postscriptOtherBlues = [-260, -220]

    font = extrapolate_font(light, bold, design_t(750))  # t = 1.125

    assert font.info.postscriptBlueValues == [-42, 0, 722, 765]
    assert font.info.postscriptStemSnapH == [130]
    assert font.info.postscriptStemSnapV == [140]
    assert font.info.postscriptOtherBlues == [-268, -225]


def test_extrapolated_font_carries_panose(micro_masters):
    # F7/PANOSE: the family-constant classification is copied to the Bold.
    light, bold = micro_masters
    font = extrapolate_font(light, bold, design_t(750))
    assert font.info.openTypeOS2Panose == [2, 11, 8, 9, 5, 0, 0, 2, 0, 4]


def test_extrapolated_font_copies_feature_writer_lib(micro_masters):
    # Bold must compile with the same ufo2ft feature writers / glyph order as
    # its interpolated siblings, which inherit them from the masters.
    light, bold = micro_masters
    light.lib["public.glyphOrder"] = ["I", "O", "Iacute", "acutecomb", ".notdef"]
    light.lib["com.github.googlei18n.ufo2ft.featureWriters"] = [
        {"class": "KernFeatureWriter"}
    ]
    light.lib["com.github.googlei18n.ufo2ft.filters"] = [{"name": "eraseOpenCorners"}]
    font = extrapolate_font(light, bold, design_t(750))
    assert font.lib["public.glyphOrder"] == ["I", "O", "Iacute", "acutecomb", ".notdef"]
    assert font.lib["com.github.googlei18n.ufo2ft.featureWriters"] == [
        {"class": "KernFeatureWriter"}
    ]
    assert font.lib["com.github.googlei18n.ufo2ft.filters"] == [
        {"name": "eraseOpenCorners"}
    ]


def test_hint_list_pair_count_mismatch_raises(micro_masters):
    light, bold = micro_masters
    light.info.postscriptBlueValues = [-20, 0, 700, 720]
    bold.info.postscriptBlueValues = [-40, 0, 720]  # one short
    with pytest.raises(IncompatibleMastersError, match="pair counts"):
        extrapolate_font(light, bold, design_t(750))


def test_hint_list_non_monotonic_result_raises(micro_masters):
    # A blue-zone ordering violation after extrapolation must fail the build.
    light, bold = micro_masters
    light.info.postscriptBlueValues = [0, 100, 200, 300]
    bold.info.postscriptBlueValues = [0, 100, 500, 300]  # 500 > 300: overlap
    with pytest.raises(IncompatibleMastersError, match="strictly increasing"):
        extrapolate_font(light, bold, design_t(750))


def test_extrapolated_font_skips_absent_cff_hint_lists(micro_masters):
    # Masters without blue zones must not crash and leave the field unset.
    light, bold = micro_masters
    assert light.info.postscriptBlueValues is None
    font = extrapolate_font(light, bold, design_t(750))
    assert font.info.postscriptBlueValues is None


def test_extrapolated_font_copies_glyph_governance_lib(micro_masters):
    # F6: skip-export and production-name lib keys must ride along, or the
    # Bold binary leaks build parts (advanceWidthMax break) and Glyphs
    # nice-names instead of uniXXXX.
    light, bold = micro_masters
    light.lib["public.skipExportGlyphs"] = ["_part.demo"]
    light.lib["public.postscriptNames"] = {"I": "uni0049"}
    font = extrapolate_font(light, bold, design_t(750))
    assert font.lib["public.skipExportGlyphs"] == ["_part.demo"]
    assert font.lib["public.postscriptNames"] == {"I": "uni0049"}
    # Copies, not shared references.
    font.lib["public.skipExportGlyphs"].append("mutated")
    assert light.lib["public.skipExportGlyphs"] == ["_part.demo"]


def test_extrapolated_font_omits_absent_governance_lib(micro_masters):
    light, bold = micro_masters
    assert "public.skipExportGlyphs" not in light.lib
    font = extrapolate_font(light, bold, design_t(750))
    assert "public.skipExportGlyphs" not in font.lib
    assert "public.postscriptNames" not in font.lib


def test_extrapolated_font_carries_original_width_lib(micro_masters):
    # F1/F2: the per-glyph originalWidth key must survive so features.py can
    # restore the spacing overlays' 1200 advance on the Bold.
    from fira_code_chunky.extrapolate import ORIGINAL_WIDTH_KEY

    light, bold = micro_masters
    light["acutecomb"].lib[ORIGINAL_WIDTH_KEY] = 1200
    font = extrapolate_font(light, bold, design_t(750))
    assert font["acutecomb"].lib[ORIGINAL_WIDTH_KEY] == 1200
    # A glyph without the key stays clean.
    assert ORIGINAL_WIDTH_KEY not in font["I"].lib


def test_stem_monotonic_guard():
    assert stem_widths_monotonic([50, 70, 120, 130])
    assert not stem_widths_monotonic([50, 70, 120, 119])
    assert not stem_widths_monotonic([50, 50, 120, 130])
