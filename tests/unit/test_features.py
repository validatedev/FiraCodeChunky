import io

import pytest
import ufoLib2
from fontTools.feaLib.parser import Parser

from fira_code_chunky.features import ensure_opentype_categories, sanitize_features

# Upstream Fira Code stores character-variant UI labels as `featureNames`
# blocks inside cvXX features. feaLib only accepts `featureNames` in stylistic
# sets (ssXX); cvXX must use `cvParameters { FeatUILabelNameID { ... } }`.
CV_SOURCE = """\
feature cv01 {
featureNames {
  name "alternate lowercase a";
};
# automatic
sub a by a.cv01;
} cv01;

feature ss01 {
featureNames {
  name "stylistic set one";
};
sub a by a.ss01;
} ss01;

feature calt {
sub a by a.ss01;
} calt;
"""


def _parse(text):
    Parser(
        io.StringIO(text),
        glyphNames={"a", "a.cv01", "a.ss01"},
    ).parse()


def test_raw_cv_feature_names_is_rejected_by_fealib():
    try:
        _parse(CV_SOURCE)
    except Exception as error:
        assert "featureNames" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected feaLib to reject cvXX featureNames")


def test_sanitize_rewrites_cv_feature_names_to_cvparameters():
    fixed = sanitize_features(CV_SOURCE)

    assert "cvParameters {" in fixed
    assert "FeatUILabelNameID {" in fixed
    assert 'name "alternate lowercase a";' in fixed
    # ssXX featureNames must be preserved verbatim.
    assert 'featureNames {\n  name "stylistic set one";' in fixed
    _parse(fixed)  # now compiles


def test_sanitize_is_identity_without_cv_features():
    plain = "feature calt {\nsub a by a.ss01;\n} calt;\n"
    assert sanitize_features(plain) == plain


def test_sanitize_handles_empty_text():
    assert sanitize_features("") == ""


def _spacing_grave_ufo() -> ufoLib2.Font:
    """Minimal UFO: spacing grave (U+0060) + true combining gravecomb.

    Both carry a ``_top`` mark anchor (as in Fira Code). Without categories,
    ufo2ft would mark-class both; with categories only gravecomb is a mark.
    """
    font = ufoLib2.Font()
    font.info.unitsPerEm = 1000
    font.info.familyName = "Test"
    font.info.styleName = "Regular"
    grave = font.newGlyph("grave")
    grave.unicodes = [0x60]
    grave.width = 1200
    grave.appendAnchor({"name": "_top", "x": 600, "y": 700})
    comb = font.newGlyph("gravecomb")
    comb.unicodes = [0x300]
    comb.width = 0
    comb.appendAnchor({"name": "_top", "x": 600, "y": 700})
    base = font.newGlyph("S")
    base.unicodes = [0x53]
    base.width = 1200
    base.appendAnchor({"name": "top", "x": 600, "y": 700})
    return font


def test_ensure_opentype_categories_keeps_spacing_grave_out_of_mark_class():
    font = _spacing_grave_ufo()

    categories = ensure_opentype_categories(font)

    assert categories.get("gravecomb") == "mark"
    assert categories.get("grave") != "mark"
    assert "grave" not in categories or categories["grave"] != "mark"
    assert font.lib["public.openTypeCategories"].get("gravecomb") == "mark"
    assert font.lib["public.openTypeCategories"].get("grave") != "mark"


def test_ensure_opentype_categories_empty_font_is_noop():
    font = ufoLib2.Font()
    font.info.unitsPerEm = 1000
    assert ensure_opentype_categories(font) == {}
    assert "public.openTypeCategories" not in font.lib


def test_ensure_opentype_categories_drops_stale_lib_map():
    font = ufoLib2.Font()
    font.info.unitsPerEm = 1000
    font.lib["public.openTypeCategories"] = {"strokeshortoverlay": "mark"}
    assert ensure_opentype_categories(font) == {}
    assert "public.openTypeCategories" not in font.lib


_ORIGINAL_WIDTH_KEY = "com.schriftgestaltung.Glyphs.originalWidth"


def _spacing_overlay_ufo() -> ufoLib2.Font:
    """UFO with the U+0335 overlay (a spacing override) + a true combining mark.

    Both are glyphsLib-classified as marks with a zeroed advance; only the
    overlay must be un-marked and re-spaced (F1). ``commaaccent`` (U+0326, the
    non-.case comma-below) is a genuine mark that must stay a mark.
    """
    font = ufoLib2.Font()
    font.info.unitsPerEm = 1000
    font.info.familyName = "Test"
    font.info.styleName = "Regular"
    overlay = font.newGlyph("strokeshortoverlay")
    overlay.unicodes = [0x0335]
    overlay.width = 0
    overlay.lib[_ORIGINAL_WIDTH_KEY] = 1200
    comb = font.newGlyph("commaaccent")
    comb.unicodes = [0x0326]
    comb.width = 0
    comb.lib[_ORIGINAL_WIDTH_KEY] = 1200
    return font


def test_spacing_overlay_is_unmarked_and_respaced():
    font = _spacing_overlay_ufo()

    categories = ensure_opentype_categories(font)

    # Overlay: dropped from categories (GDEF-unclassified) and re-spaced to 1200.
    assert "strokeshortoverlay" not in categories
    assert font["strokeshortoverlay"].width == 1200
    # True combining comma-below stays a zero-advance mark.
    assert categories.get("commaaccent") == "mark"
    assert font["commaaccent"].width == 0


def test_spacing_overlay_without_original_width_is_hard_error():
    # A spacing override that lost its originalWidth cannot be re-spaced; the
    # build must fail loudly rather than ship a collapsed zero-advance glyph.
    from fira_code_chunky.qa import QAError

    font = _spacing_overlay_ufo()
    del font["strokeshortoverlay"].lib[_ORIGINAL_WIDTH_KEY]
    font["strokeshortoverlay"].width = 0

    with pytest.raises(QAError, match="originalWidth"):
        ensure_opentype_categories(font)


def test_spacing_overlay_with_zero_original_width_is_hard_error():
    from fira_code_chunky.qa import QAError

    font = _spacing_overlay_ufo()
    font["strokeshortoverlay"].lib[_ORIGINAL_WIDTH_KEY] = 0

    with pytest.raises(QAError, match="originalWidth"):
        ensure_opentype_categories(font)


def test_spacing_overrides_are_a_frozen_allowlist():
    # Exactly three glyphs are spacing in official Fira Code 6.002; the other 19
    # width-0/originalWidth-1200 glyphs are genuine marks. Freeze the set so a
    # careless generalization on originalWidth cannot creep in.
    from fira_code_chunky.features import _SPACING_OVERRIDES

    assert _SPACING_OVERRIDES == (
        "strokeshortoverlay",
        "strokelongoverlay",
        "commaaccent.case",
    )
