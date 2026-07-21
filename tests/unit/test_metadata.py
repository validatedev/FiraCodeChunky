from fontTools.ttLib import TTFont

from fira_code_chunky.metadata import (
    pin_all,
    pin_names,
    pin_style_bits,
    pin_weight_class,
    rename_cff,
)

WIN = (3, 1, 0x409)


def reopened(font, tmp_path):
    path = tmp_path / "out.ttf"
    font.save(path)
    return TTFont(path)


def name(font, name_id):
    record = font["name"].getName(name_id, *WIN)
    return None if record is None else record.toUnicode()


def test_pin_weight_class_persists(micro_ttf, tmp_path):
    pin_weight_class(micro_ttf, 400)
    assert reopened(micro_ttf, tmp_path)["OS/2"].usWeightClass == 400


def test_style_bits_regular(micro_ttf, tmp_path):
    micro_ttf["OS/2"].fsSelection |= 1 << 7
    pin_style_bits(micro_ttf, "Regular")
    font = reopened(micro_ttf, tmp_path)
    assert font["OS/2"].fsSelection & (1 << 6)
    assert not font["OS/2"].fsSelection & (1 << 5)
    assert font["OS/2"].fsSelection & (1 << 7)
    assert not font["head"].macStyle & 1


def test_style_bits_bold(micro_ttf, tmp_path):
    pin_style_bits(micro_ttf, "Bold")
    font = reopened(micro_ttf, tmp_path)
    assert font["OS/2"].fsSelection & (1 << 5)
    assert not font["OS/2"].fsSelection & (1 << 6)
    assert font["head"].macStyle & 1


def test_names_ribbi_regular(micro_ttf, tmp_path):
    pin_names(micro_ttf, "Fira Code Chunky", "Regular")
    font = reopened(micro_ttf, tmp_path)
    assert name(font, 1) == "Fira Code Chunky"
    assert name(font, 2) == "Regular"
    assert name(font, 3) == "1.0;chunky;FiraCodeChunky-Regular"
    assert name(font, 4) == "Fira Code Chunky Regular"
    assert name(font, 6) == "FiraCodeChunky-Regular"
    assert name(font, 16) is None
    assert name(font, 17) is None


def test_names_non_ribbi_medium(micro_ttf, tmp_path):
    pin_names(micro_ttf, "Fira Code Chunky", "Medium")
    font = reopened(micro_ttf, tmp_path)
    assert name(font, 1) == "Fira Code Chunky Medium"
    assert name(font, 2) == "Regular"
    assert name(font, 16) == "Fira Code Chunky"
    assert name(font, 17) == "Medium"
    assert name(font, 4) == "Fira Code Chunky Medium"
    assert name(font, 6) == "FiraCodeChunky-Medium"
    assert name(font, 3) is not None


def test_pin_all(micro_ttf, tmp_path):
    pin_all(micro_ttf, "Fira Code Chunky", "SemiBold", 600)
    font = reopened(micro_ttf, tmp_path)
    assert font["OS/2"].usWeightClass == 600
    assert font["OS/2"].usWidthClass == 5
    assert font["post"].isFixedPitch == 1
    assert name(font, 17) == "SemiBold"
    assert font["OS/2"].fsSelection & (1 << 6)
    assert not font["OS/2"].fsSelection & (1 << 5)
    assert font["head"].macStyle & 1 == 0


def test_rename_cff_noop_on_ttf(micro_ttf, tmp_path):
    rename_cff(
        micro_ttf,
        "FiraCodeChunky-Regular",
        "Fira Code Chunky",
        "Fira Code Chunky Regular",
    )
    assert "CFF " not in reopened(micro_ttf, tmp_path)


def test_rename_cff_persists(micro_otf, tmp_path):
    rename_cff(
        micro_otf,
        "FiraCodeChunky-Regular",
        "Fira Code Chunky",
        "Fira Code Chunky Regular",
    )
    font = reopened(micro_otf, tmp_path)
    cff = font["CFF "].cff
    assert cff.fontNames[0] == "FiraCodeChunky-Regular"
    assert cff.topDictIndex[0].FamilyName == "Fira Code Chunky"
    assert cff.topDictIndex[0].FullName == "Fira Code Chunky Regular"
