"""Mark-attachment anchoring pins, including the deliberate dot-above fix.

Chunky rebuilds the GPOS mark feature and places U+0307 (dot above) correctly
ABOVE the base (positive y_offset ~324 on D), where official Fira Code
mis-anchors it ~960 units too low. These pins protect that divergence and a
small base x mark matrix from silent regression, in Regular and Bold.
"""

from pathlib import Path

import pytest

from fira_code_chunky import qa_deep

pytestmark = pytest.mark.integration

DIST = Path("dist")
requires_dist = pytest.mark.skipif(
    not (DIST / "ttf" / "FiraCodeChunky-Regular.ttf").exists(),
    reason="need dist/ttf statics (run chunky-build)",
)


def _mark_offset(path: Path, text: str, mark_glyph: str) -> tuple[int, int]:
    shaped = qa_deep.shaped_positions(path, text)
    for name, _adv, x_off, y_off in shaped:
        if name == mark_glyph:
            return x_off, y_off
    raise AssertionError(f"{mark_glyph} not in shaped {text!r}: {shaped}")


@requires_dist
@pytest.mark.parametrize("style", ["Regular", "Bold"])
def test_dot_above_anchors_above_the_base(style):
    # D + U+0307 (uni0307): the dot must sit ABOVE the cap, i.e. a clearly
    # positive y_offset, not the sunk-in negative placement of official.
    path = DIST / "ttf" / f"FiraCodeChunky-{style}.ttf"
    _x_off, y_off = _mark_offset(path, "Ḋ", "uni0307")
    assert y_off > 250, (
        f"{style}: dot-above y_offset {y_off} should be clearly positive"
    )
    # Ascender base (l) lifts the dot even higher than the cap base (D).
    _x_off, y_off_l = _mark_offset(path, "l̇", "uni0307")
    assert y_off_l >= y_off


@requires_dist
@pytest.mark.parametrize("style", ["Regular", "Bold"])
@pytest.mark.parametrize("base", ["D", "H", "l", "x"])
@pytest.mark.parametrize("mark_cp", [0x0307, 0x0304])  # dot above, macron
def test_mark_matrix_attaches_without_a_cell(style, base, mark_cp):
    # A base + combining top-mark stays two glyphs: the base keeps its 1200
    # cell and the mark attaches with a zero advance and a nonzero placement
    # (it never consumes a cell of its own).
    path = DIST / "ttf" / f"FiraCodeChunky-{style}.ttf"
    shaped = qa_deep.shaped_positions(path, base + chr(mark_cp))
    assert len(shaped) == 2, f"{style} {base}+U{mark_cp:04X}: {shaped}"
    (_bname, base_adv, _bx, _by), (mname, adv, x_off, y_off) = shaped
    assert base_adv == 1200
    assert adv == 0, f"{style} {base}+U{mark_cp:04X}: {mname} advance {adv} != 0"
    assert (x_off, y_off) != (0, 0), f"{style} {base}+U{mark_cp:04X}: {mname} unplaced"
