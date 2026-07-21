"""Assemble and finalize the 3-master variable font.

The static build bakes five instance UFOs at design locations that follow
upstream's piecewise weight curve (identity for the micro fixture, [73, 96,
122, 145, 171] for real Fira Code). Each baked UFO records its design location
in ``font.lib`` under :data:`VF_DESIGN_LOCATION_KEY`. This module reads those
UFOs back, keeps the three that sit at the fvar boundaries and default (Light,
Regular, Bold), and emits a designspace whose ``avar`` map (all five user ->
design pairs) reproduces the curve while the fvar axis stays 300/400/700.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import ufoLib2
from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    SourceDescriptor,
)
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont

from fira_code_chunky import FAMILY_NAME, VF_DESIGN_LOCATION_KEY, WEIGHT_CLASSES
from fira_code_chunky.metadata import WIN
from fira_code_chunky.qa import QAError

AXIS_NAME = "Weight"

# STAT weight-axis values mirroring the official FiraCode-VF: five format-2
# ranges (one per named weight) plus a format-3 style link from the elidable
# Regular to Bold. ELIDABLE (0x2) hides "Regular" from composed style names.
# Without these records apps cannot resolve named instances from the VF (F9).
_ELIDABLE = 0x2
_STAT_AXES = [
    {
        "tag": "wght",
        "name": AXIS_NAME,
        "values": [
            {
                "name": "Light",
                "nominalValue": 300,
                "rangeMinValue": 300,
                "rangeMaxValue": 350,
            },
            {
                "name": "Regular",
                "nominalValue": 400,
                "rangeMinValue": 350,
                "rangeMaxValue": 450,
                "flags": _ELIDABLE,
            },
            {
                "name": "Medium",
                "nominalValue": 500,
                "rangeMinValue": 450,
                "rangeMaxValue": 550,
            },
            {
                "name": "SemiBold",
                "nominalValue": 600,
                "rangeMinValue": 550,
                "rangeMaxValue": 650,
            },
            {
                "name": "Bold",
                "nominalValue": 700,
                "rangeMinValue": 650,
                "rangeMaxValue": 700,
            },
            {"name": "Regular", "value": 400, "linkedValue": 700, "flags": _ELIDABLE},
        ],
    }
]


def _read_baked(
    instance_dir: Path,
) -> tuple[list[tuple[int, float, Path, str]], list[str]]:
    """Return sorted (user, design, path, style) entries + skip-export glyphs.

    The skip-export list is taken from the default (Regular) master so the VF
    designspace can honor it; without it ufo2ft leaks build parts such as
    ``_part.numbersign`` into the variable font (F6).
    """
    entries: list[tuple[int, float, Path, str]] = []
    skip_export: list[str] = []
    for ufo_path in sorted(instance_dir.glob("FiraCodeChunky-*.ufo")):
        font = ufoLib2.Font.open(ufo_path)
        user = int(cast(int, font.info.openTypeOS2WeightClass))
        design = float(cast(float, font.lib[VF_DESIGN_LOCATION_KEY]))
        style = str(font.info.styleName)
        if user == WEIGHT_CLASSES["Regular"]:
            skip_export = list(font.lib.get("public.skipExportGlyphs", []))
        entries.append((user, design, ufo_path, style))
    return sorted(entries), skip_export


def build_vf_designspace(instance_dir: Path, out_path: Path) -> DesignSpaceDocument:
    """Build a 3-master VF designspace whose avar map carries the weight curve."""
    entries, skip_export = _read_baked(instance_dir)
    users = [user for user, *_ in entries]
    default_user = WEIGHT_CLASSES["Regular"]
    master_users = {min(users), default_user, max(users)}

    ds = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.tag = "wght"
    axis.name = AXIS_NAME
    axis.minimum = min(users)
    axis.default = default_user
    axis.maximum = max(users)
    axis.map = [(float(user), design) for user, design, *_ in entries]
    ds.addAxis(axis)

    for user, design, ufo_path, style in entries:
        if user not in master_users:
            continue
        source = SourceDescriptor()
        source.path = str(ufo_path)
        source.filename = ufo_path.name
        source.familyName = FAMILY_NAME
        source.styleName = style
        source.location = {AXIS_NAME: design}
        ds.addSource(source)

    if skip_export:
        ds.lib["public.skipExportGlyphs"] = skip_export

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.write(out_path)
    return ds


def finalize_vf(path: Path) -> None:
    """Assert the fvar axis, pin the family name, and leave the VF unhinted."""
    with TTFont(path) as font:
        axis = font["fvar"].axes[0]
        got = (axis.minValue, axis.defaultValue, axis.maxValue)
        if got != (300, 400, 700):
            # A bare `assert` here would be stripped under python -O and
            # would raise plain AssertionError, which run_build's except
            # tuple does not catch (Fix 3).
            raise QAError(f"fvar (min, default, max) {got} != (300, 400, 700)")
        name = font["name"]
        for name_id in (1, 16):
            if name.getName(name_id, *WIN) is not None:
                name.setName(FAMILY_NAME, name_id, *WIN)
        # Elided fallback name ID 2 (Regular) matches the official VF.
        buildStatTable(font, _STAT_AXES, elidedFallbackName=2)
        font.save(path)
