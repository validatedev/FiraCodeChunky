"""Generate the committed micro fixture. Run once: uv run python tests/fixtures/build_fixture.py"""

from pathlib import Path

import ufoLib2
from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)

HERE = Path(__file__).parent / "micro"


def rect(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()


def build_master(style, params):
    font = ufoLib2.Font()
    info = font.info
    info.familyName, info.styleName = "Micro Fira", style
    info.unitsPerEm, info.ascender, info.descender = 1000, 800, -200
    info.capHeight, info.xHeight = 700, 500
    # OFL metadata: identical across masters, mirroring how upstream Fira
    # Code carries these fields on every master UFO. Exercises Fix 1
    # (extrapolate._copy_info must propagate them to the synthetic Bold).
    info.copyright = "Copyright 2014-2021 The Micro Fira Project Authors"
    info.trademark = "Micro Fira is a trademark of the Micro Fira Project Authors."
    info.openTypeNameLicense = (
        "This Font Software is licensed under the SIL Open Font License, Version 1.1."
    )
    info.openTypeNameLicenseURL = "http://scripts.sil.org/OFL"
    info.openTypeOS2VendorID = "MICR"
    info.versionMajor, info.versionMinor = 6, 2
    # Family-constant metadata the synthetic Bold must inherit (extrapolate
    # copies these verbatim; QA asserts them per static):
    #   installable embedding (F5), USE_TYPO_METRICS (F7), the family's constant
    #   underline/strikeout geometry (F4), and designer/manufacturer records
    #   that populate name IDs 8/9/11/12 (F7).
    info.openTypeOS2Type = []
    info.openTypeOS2Selection = [7]
    info.postscriptUnderlinePosition = -100
    info.postscriptUnderlineThickness = 50
    info.openTypeOS2StrikeoutPosition = 318
    info.openTypeOS2StrikeoutSize = 50
    info.openTypeNameDesigner = "The Micro Fira Project Authors"
    info.openTypeNameDesignerURL = "https://example.invalid/designer"
    info.openTypeNameManufacturer = "The Micro Fira Project Authors"
    info.openTypeNameManufacturerURL = "https://example.invalid/manufacturer"

    g = font.newGlyph(".notdef")
    g.width = 600
    rect(g.getPen(), 50, 0, 550, 700)

    g = font.newGlyph("I")
    g.width = 600
    rect(g.getPen(), params["i_left"], 0, params["i_right"], 700)
    g.appendAnchor({"name": "top", "x": 300, "y": params["i_top_y"]})

    g = font.newGlyph("O")
    g.width = 600
    o = params["o_outer"]
    i = params["o_inner"]
    rect(g.getPen(), o[0], o[1], o[2], o[3])
    rect(g.getPen(), i[0], i[1], i[2], i[3])

    g = font.newGlyph("acutecomb")
    g.width = 0
    a = params["acute"]
    rect(g.getPen(), a[0], a[1], a[2], a[3])
    g.appendAnchor({"name": "_top", "x": 300, "y": a[1]})

    g = font.newGlyph("Iacute")
    g.width = 600
    pen = g.getPen()
    pen.addComponent("I", (1, 0, 0, 1, 0, 0))
    pen.addComponent("acutecomb", (1, 0, 0, 1, 0, params["acute_dy"]))

    font.kerning[("I", "O")] = params["kern"]
    font.features.text = "feature calt { sub I' O by Iacute; } calt;\n"
    return font


LIGHT = {
    "i_left": 280,
    "i_right": 320,
    "i_top_y": 700,
    "o_outer": (100, 0, 500, 700),
    "o_inner": (180, 80, 420, 620),
    "acute": (280, 520, 320, 640),
    "acute_dy": 180,
    "kern": -8,
}
BOLD = {
    "i_left": 240,
    "i_right": 360,
    "i_top_y": 720,
    "o_outer": (60, 0, 540, 700),
    "o_inner": (200, 120, 400, 580),
    "acute": (260, 540, 340, 700),
    "acute_dy": 200,
    "kern": -40,
}


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    build_master("Light", LIGHT).save(HERE / "MicroLight.ufo", overwrite=True)
    build_master("Bold", BOLD).save(HERE / "MicroBold.ufo", overwrite=True)

    ds = DesignSpaceDocument()
    axis = AxisDescriptor(
        tag="wght", name="Weight", minimum=300, default=300, maximum=700
    )
    ds.addAxis(axis)
    for filename, style, loc in [
        ("MicroLight.ufo", "Light", 300),
        ("MicroBold.ufo", "Bold", 700),
    ]:
        src = SourceDescriptor(
            filename=filename,
            styleName=style,
            familyName="Micro Fira",
            location={"Weight": loc},
        )
        ds.addSource(src)
    for style, loc in [
        ("Light", 300),
        ("Regular", 400),
        ("Retina", 450),
        ("Medium", 500),
        ("SemiBold", 600),
        ("Bold", 700),
    ]:
        inst = InstanceDescriptor(
            familyName="Micro Fira", styleName=style, location={"Weight": loc}
        )
        ds.addInstance(inst)
    ds.write(HERE / "Micro.designspace")


if __name__ == "__main__":
    main()
