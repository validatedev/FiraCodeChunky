from pathlib import Path
from typing import Any, cast

import pytest
from fontTools.ttLib import TTFont

pytestmark = pytest.mark.integration
DIST = Path("dist")
requires_dist = pytest.mark.skipif(not DIST.exists(), reason="run chunky-build first")


@requires_dist
@pytest.mark.parametrize(
    ("style", "wc"),
    [
        ("Light", 300),
        ("Regular", 400),
        ("Medium", 500),
        ("SemiBold", 600),
        ("Bold", 700),
    ],
)
def test_static_weight_classes(style, wc):
    font = TTFont(DIST / "ttf" / f"FiraCodeChunky-{style}.ttf")
    assert cast(Any, font["OS/2"]).usWeightClass == wc


@requires_dist
def test_vf_axis():
    font = TTFont(DIST / "variable" / "FiraCodeChunky-VF.ttf")
    axis = font["fvar"].axes[0]
    assert (axis.minValue, axis.defaultValue, axis.maxValue) == (300, 400, 700)
    assert "avar" in font  # piecewise map 300->73 etc. materializes as avar


@requires_dist
def test_vf_avar_carries_upstream_curve():
    # The avar table must place each named user weight at upstream's piecewise
    # design coordinate. fvar range 300/400/700 and master design span
    # 73/96/171 both normalize about the default; the avar segment maps the
    # user normalization onto the design normalization.
    font = TTFont(DIST / "variable" / "FiraCodeChunky-VF.ttf")
    seg = font["avar"].segments["wght"]

    def norm(value, lo, default, hi):
        if value >= default:
            return (value - default) / (hi - default)
        return (value - default) / (default - lo)

    checks = {300: 73, 400: 96, 500: 122, 600: 145, 700: 171}
    for user, design in checks.items():
        in_norm = norm(user, 300, 400, 700)
        key = min(seg, key=lambda k: abs(k - in_norm))
        assert abs(key - in_norm) < 1e-4
        design_norm = norm(design, 73, 96, 171)
        assert seg[key] == pytest.approx(design_norm, abs=1e-3)


@requires_dist
def test_statics_are_hinted_vf_is_not():
    reg = TTFont(DIST / "ttf" / "FiraCodeChunky-Regular.ttf")
    vf = TTFont(DIST / "variable" / "FiraCodeChunky-VF.ttf")
    assert cast(Any, reg["maxp"]).maxSizeOfInstructions > 0
    assert cast(Any, vf["maxp"]).maxSizeOfInstructions == 0
