"""Backtick / spacing-grave must not attach as a combining mark.

Regression for the user-visible bug where ``S` `` and `` `word` `` rendered as
a grave over the neighboring letter. Root cause: GDEF mark class on spacing
``grave`` (U+0060). Official Fira Code leaves that glyph out of GDEF marks so
HarfBuzz keeps its full advance.
"""

from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from fira_code_chunky import qa_deep

pytestmark = pytest.mark.integration

DIST_REGULAR = Path("dist/ttf/FiraCodeChunky-Regular.ttf")
requires_dist = pytest.mark.skipif(
    not DIST_REGULAR.exists(),
    reason="need dist/ttf/FiraCodeChunky-Regular.ttf (run chunky-build)",
)


@requires_dist
def test_spacing_grave_is_not_gdef_mark():
    font = TTFont(DIST_REGULAR)
    class_defs = font["GDEF"].table.GlyphClassDef.classDefs
    # 3 = mark. Spacing grave must not be classified as a mark.
    assert class_defs.get("grave") != 3
    assert class_defs.get("grave.case") != 3
    # True combining grave stays a mark.
    assert class_defs.get("gravecomb") == 3


@requires_dist
@pytest.mark.parametrize(
    "text",
    [
        "S`",
        "`x`",
        "`pond`",
        "`MIS_DOCS`",
        "a`b",
        "x `y` z",
    ],
)
def test_backtick_shapes_as_standalone_with_full_advance(text):
    """Each grave/backtick glyph must keep a positive advance (not attach)."""
    shaped = qa_deep.shaped_advances(DIST_REGULAR, text)
    graves = [(name, adv) for name, adv in shaped if name.startswith("grave")]
    assert graves, f"expected grave glyph(s) in shaped stream for {text!r}: {shaped}"
    for name, adv in graves:
        assert adv > 0, (
            f"{text!r}: {name} advanced {adv} (expected full cell); full stream {shaped}"
        )
