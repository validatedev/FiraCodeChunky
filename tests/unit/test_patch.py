import pytest

from fira_code_chunky import FAMILY_NAME
from fira_code_chunky.patch import (
    axis_name,
    drop_instance,
    make_chunky,
    rename_family,
    shift_instance_locations,
)


def loc(inst, ds):
    return inst.location[axis_name(ds)]


def test_drop_instance(micro_ds):
    drop_instance(micro_ds, "Retina")
    assert [i.styleName for i in micro_ds.instances] == [
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
    ]


def test_drop_missing_instance_raises(micro_ds):
    with pytest.raises(ValueError, match="Nope"):
        drop_instance(micro_ds, "Nope")


def test_shift_locations(micro_ds):
    drop_instance(micro_ds, "Retina")
    shift_instance_locations(micro_ds, 50)
    assert [loc(i, micro_ds) for i in micro_ds.instances] == [350, 450, 550, 650, 750]
    wght = micro_ds.axes[0]
    assert wght.maximum == 750  # extended to cover shifted Bold


def test_rename_family_ribbi(micro_ds):
    drop_instance(micro_ds, "Retina")
    rename_family(micro_ds, FAMILY_NAME)
    by_style = {i.styleName: i for i in micro_ds.instances}
    reg, med = by_style["Regular"], by_style["Medium"]
    assert reg.familyName == FAMILY_NAME
    assert reg.postScriptFontName == "FiraCodeChunky-Regular"
    assert reg.styleMapFamilyName == FAMILY_NAME
    assert reg.styleMapStyleName == "regular"
    assert by_style["Bold"].styleMapStyleName == "bold"
    assert med.styleMapFamilyName == f"{FAMILY_NAME} Medium"
    assert med.styleMapStyleName == "regular"


def test_make_chunky_composes(micro_ds):
    make_chunky(micro_ds)
    assert len(micro_ds.instances) == 5
    assert all(i.familyName == FAMILY_NAME for i in micro_ds.instances)
    assert [loc(i, micro_ds) for i in micro_ds.instances] == [350, 450, 550, 650, 750]


def test_axis_name_raises_without_wght_axis():
    from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument

    ds = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.tag = "wdth"
    axis.name = "Width"
    ds.addAxis(axis)

    with pytest.raises(ValueError, match="no wght axis"):
        axis_name(ds)


def test_shift_locations_does_not_lower_axis_maximum(micro_ds):
    wght = micro_ds.axes[0]
    original_max = wght.maximum
    shift_instance_locations(micro_ds, 0)
    assert wght.maximum == original_max


def test_patch_survives_save_reload(micro_ds, tmp_path):
    from fontTools.designspaceLib import DesignSpaceDocument

    make_chunky(micro_ds)
    out = tmp_path / "chunky.designspace"
    micro_ds.write(out)
    reloaded = DesignSpaceDocument.fromfile(out)
    assert [i.styleName for i in reloaded.instances] == [
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
    ]
    assert reloaded.instances[1].postScriptFontName == "FiraCodeChunky-Regular"
