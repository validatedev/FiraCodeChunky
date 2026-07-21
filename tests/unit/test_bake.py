from fira_code_chunky import FAMILY_NAME, WEIGHT_CLASSES
from fira_code_chunky.bake import apply_instance_metadata, bake_interior_instances
from fira_code_chunky.patch import make_chunky


def bake(micro_ds):
    make_chunky(micro_ds)
    return bake_interior_instances(micro_ds)


def test_bakes_only_in_range_instances(micro_ds):
    baked = bake(micro_ds)
    assert [inst.styleName for inst, _ in baked] == [
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
    ]


def test_regular_450_matches_hand_math(micro_ds):
    baked = {inst.styleName: font for inst, font in bake(micro_ds)}
    regular = baked["Regular"]  # design 450, t = 0.375
    xs = sorted({p.x for p in regular["I"].contours[0].points})
    assert xs == [265, 335]  # 280 - 0.375*40, 320 + 0.375*40
    assert regular.kerning[("I", "O")] == -20  # -8 - 0.375*32
    assert regular["I"].anchors[0].y == 708  # round(707.5) with round_geometry


def test_metadata_regular_vs_medium(micro_ds):
    pairs = bake(micro_ds)
    for inst, font in pairs:
        apply_instance_metadata(font, inst, WEIGHT_CLASSES[inst.styleName])
    by_style = {inst.styleName: font for inst, font in pairs}
    reg, med = by_style["Regular"], by_style["Medium"]
    assert reg.info.openTypeOS2WeightClass == 400
    assert reg.info.familyName == FAMILY_NAME
    assert reg.info.styleMapStyleName == "regular"
    assert reg.info.openTypeNamePreferredFamilyName is None
    assert med.info.openTypeOS2WeightClass == 500
    assert med.info.styleMapFamilyName == f"{FAMILY_NAME} Medium"
    assert med.info.openTypeNamePreferredFamilyName == FAMILY_NAME
    assert med.info.openTypeNamePreferredSubfamilyName == "Medium"
    assert med.info.postscriptFontName == "FiraCodeChunky-Medium"
