from typing import Any, cast

import pytest
from fontTools.designspaceLib import AxisDescriptor
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from fira_code_chunky import FAMILY_NAME, pipeline, variable
from fira_code_chunky.metadata import WIN
from fira_code_chunky.patch import make_chunky
from fira_code_chunky.qa import QAError


def test_vf_designspace_structure(micro_ds, tmp_path):
    make_chunky(micro_ds)
    baked = pipeline.bake_all(micro_ds)
    inst_dir = tmp_path / "instances"
    inst_dir.mkdir()
    for style, font in baked:
        font.save(inst_dir / f"FiraCodeChunky-{style}.ufo", overwrite=True)

    ds = variable.build_vf_designspace(inst_dir, tmp_path / "vf.designspace")

    axis = ds.axes[0]
    assert isinstance(axis, AxisDescriptor)
    assert (axis.minimum, axis.default, axis.maximum) == (300, 400, 700)
    # Amendment: identity micro map yields design(user+50) == user+50, so the
    # 5-entry VF map materializes as [(300,350),(400,450),(500,550),...].
    assert axis.map == [
        (300, 350),
        (400, 450),
        (500, 550),
        (600, 650),
        (700, 750),
    ]
    locs = sorted(s.location[axis.name] for s in ds.sources)
    assert locs == [350, 450, 750]  # Light / Regular(default) / Bold masters
    default = [s for s in ds.sources if s.location[axis.name] == 450]
    assert len(default) == 1  # Regular/Retina design is the default master
    assert (tmp_path / "vf.designspace").exists()


def _synthetic_vf(path, *, family, with_typographic, axis_range=(300, 400, 700)):
    fb = FontBuilder(unitsPerEm=1000, isTTF=True)
    fb.setupGlyphOrder([".notdef"])
    fb.setupCharacterMap({})
    pen = TTGlyphPen(None)
    fb.setupGlyf({".notdef": pen.glyph()})
    fb.setupHorizontalMetrics({".notdef": (500, 0)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    if with_typographic:
        fb.font["name"].setName(family, 16, *WIN)
    fb.setupOS2()
    fb.setupPost()
    minv, defv, maxv = axis_range
    fb.setupFvar(
        axes=[("wght", minv, defv, maxv, "Weight")],
        instances=[],
    )
    fb.font.save(path)
    return path


def test_finalize_vf_pins_family_and_leaves_unhinted(tmp_path):
    path = _synthetic_vf(
        tmp_path / "vf.ttf", family="Placeholder", with_typographic=True
    )

    variable.finalize_vf(path)

    font = TTFont(path)
    axis = font["fvar"].axes[0]
    assert (axis.minValue, axis.defaultValue, axis.maxValue) == (300, 400, 700)
    assert cast(Any, font["name"]).getName(1, *WIN).toUnicode() == FAMILY_NAME
    assert cast(Any, font["name"]).getName(16, *WIN).toUnicode() == FAMILY_NAME
    assert cast(Any, font["maxp"]).maxSizeOfInstructions == 0


def test_finalize_vf_raises_qa_error_on_wrong_fvar_range(tmp_path):
    # Fix 3: the fvar (300,400,700) invariant must raise qa.QAError, not a
    # bare AssertionError that -O would strip and that run_build's except
    # tuple doesn't catch.
    path = _synthetic_vf(
        tmp_path / "vf.ttf",
        family="Placeholder",
        with_typographic=True,
        axis_range=(300, 400, 900),
    )

    with pytest.raises(QAError, match="fvar"):
        variable.finalize_vf(path)


def test_finalize_vf_without_typographic_name(tmp_path):
    path = _synthetic_vf(
        tmp_path / "vf.ttf", family="Placeholder", with_typographic=False
    )

    variable.finalize_vf(path)

    font = TTFont(path)
    assert cast(Any, font["name"]).getName(1, *WIN).toUnicode() == FAMILY_NAME
    assert cast(Any, font["name"]).getName(16, *WIN) is None
