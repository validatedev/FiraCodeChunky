"""Combining overlays / comma-below must shape as full spacing cells.

Regression for F1/F2: U+0335 (strokeshortoverlay), U+0336 (strokelongoverlay)
and capital + U+0326 (ccmp -> uni0326.case) used to compile with a zero advance
and a GDEF mark class, so HarfBuzz collapsed them onto the previous glyph. The
official Fira Code 6.002 ships them as spacing glyphs (advance 1200, GDEF
unclassified), so a legitimate combining sequence keeps clean, separate cells.

Oracle: the installed official ``FiraCode-Regular.ttf`` shapes the same totals.
"""

from pathlib import Path

import pytest

from fira_code_chunky import qa_deep

pytestmark = pytest.mark.integration

DIST = Path("dist")
CELL = 1200
requires_dist = pytest.mark.skipif(
    not (DIST / "ttf" / "FiraCodeChunky-Regular.ttf").exists(),
    reason="need dist/ttf statics (run chunky-build)",
)

# (text, expected total advance in cells): a 2-cell base run plus the overlay
# must total 3 full cells; capital + comma-below totals 2 cells.
CASES = [
    ("q̵x", 3),  # U+0335 short stroke overlay
    ("a̶b", 3),  # U+0336 long stroke overlay
    ("A̦", 2),  # capital + comma-below -> uni0326.case (via ccmp)
]

STATICS = ["Light", "Regular", "Medium", "SemiBold", "Bold"]


@requires_dist
@pytest.mark.parametrize("style", STATICS)
@pytest.mark.parametrize(("text", "cells"), CASES)
def test_overlay_sequences_keep_full_cells(style, text, cells):
    path = DIST / "ttf" / f"FiraCodeChunky-{style}.ttf"
    shaped = qa_deep.shaped_advances(path, text)
    total = sum(advance for _name, advance in shaped)
    assert total == cells * CELL, f"{style} {text!r}: {shaped}"
    # Every shaped glyph occupies exactly one cell (no collapsed 0-advance mark).
    for name, advance in shaped:
        assert advance == CELL, f"{style} {text!r}: {name} advanced {advance}"


@requires_dist
@pytest.mark.parametrize(("text", "cells"), CASES)
def test_overlay_matches_official_oracle(text, cells):
    oracle = Path.home() / "Library/Fonts/FiraCode-Regular.ttf"
    if not oracle.exists():  # pragma: no cover - environment-dependent
        pytest.skip("official FiraCode-Regular.ttf not installed")
    chunky = qa_deep.shaped_advances(DIST / "ttf" / "FiraCodeChunky-Regular.ttf", text)
    official = qa_deep.shaped_advances(oracle, text)
    assert sum(a for _n, a in chunky) == sum(a for _n, a in official) == cells * CELL
