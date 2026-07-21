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


def test_stem_monotonic_guard():
    assert stem_widths_monotonic([50, 70, 120, 130])
    assert not stem_widths_monotonic([50, 70, 120, 119])
    assert not stem_widths_monotonic([50, 50, 120, 130])
