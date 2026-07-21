"""Post-build hard-pinning of binary font metadata (fontmake may recalc)."""

from __future__ import annotations

from typing import Any, cast

from fontTools.ttLib import TTFont

from fira_code_chunky import PS_FAMILY

WIN = (3, 1, 0x409)
RIBBI = {"Regular": "regular", "Bold": "bold"}
FS_BOLD, FS_REGULAR = 1 << 5, 1 << 6
MAC_BOLD = 1


def pin_weight_class(font: TTFont, value: int) -> None:
    cast(Any, font["OS/2"]).usWeightClass = value


def pin_style_bits(font: TTFont, style: str) -> None:
    os2 = cast(Any, font["OS/2"])
    os2.fsSelection &= ~(FS_BOLD | FS_REGULAR)
    head = cast(Any, font["head"])
    if style == "Bold":
        os2.fsSelection |= FS_BOLD
        head.macStyle |= MAC_BOLD
    else:
        os2.fsSelection |= FS_REGULAR
        head.macStyle &= ~MAC_BOLD


def pin_names(font: TTFont, family: str, style: str) -> None:
    name = font["name"]
    ps_name = f"{PS_FAMILY}-{style.replace(' ', '')}"
    full_name = f"{family} {style}"
    if style in RIBBI:
        records = {1: family, 2: style, 4: full_name, 6: ps_name}
        for name_id in (16, 17):
            name.removeNames(nameID=name_id)
    else:
        records = {
            1: f"{family} {style}",
            2: "Regular",
            4: full_name,
            6: ps_name,
            16: family,
            17: style,
        }
    records[3] = f"1.0;chunky;{ps_name}"
    for name_id, value in records.items():
        name.setName(value, name_id, *WIN)


def rename_cff(font: TTFont, ps_name: str, family: str, full_name: str) -> None:
    if "CFF " not in font:
        return
    cff = font["CFF "].cff
    cff.fontNames[0] = ps_name
    top = cff.topDictIndex[0]
    top.FamilyName = family
    top.FullName = full_name


def pin_all(font: TTFont, family: str, style: str, weight_class: int) -> None:
    pin_weight_class(font, weight_class)
    pin_style_bits(font, style)
    pin_names(font, family, style)
    rename_cff(
        font,
        f"{PS_FAMILY}-{style.replace(' ', '')}",
        family,
        f"{family} {style}",
    )
