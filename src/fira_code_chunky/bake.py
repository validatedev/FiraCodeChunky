"""Bake interior static instance UFOs (design 350/450/550/650).

The chunky designspace extends the weight axis maximum to 750, but the heaviest
master still sits at 700. ``Instantiator`` interpolates within the master span
only: asking it for the 750 Bold does not raise, it silently clamps to the
master model and returns wrong outlines. So this module bakes only instances at
or below the heaviest master location; the 750 Bold is extrapolated separately.
"""

from __future__ import annotations

from typing import cast

import ufoLib2
from fontmake.instantiator import Instantiator
from fontTools.designspaceLib import DesignSpaceDocument, InstanceDescriptor

from fira_code_chunky.patch import axis_name

# CFF TopDict Weight string per style. Upstream instance data mislabels Medium
# as "Semi-bold" (F8); this authoritative map corrects it and gives the
# synthetic Bold a Weight string (it had none). Regular stays "Normal" and
# SemiBold "Semi-bold" to match the correct upstream/official values.
_CFF_WEIGHT_NAMES = {
    "Light": "Light",
    "Regular": "Normal",
    "Medium": "Medium",
    "SemiBold": "Semi-bold",
    "Bold": "Bold",
}


def _in_range(ds: DesignSpaceDocument, inst: InstanceDescriptor) -> bool:
    name = axis_name(ds)
    top_master = max(source.location[name] for source in ds.sources)
    return inst.location[name] <= top_master


def bake_interior_instances(
    ds: DesignSpaceDocument,
) -> list[tuple[InstanceDescriptor, ufoLib2.Font]]:
    instantiator = Instantiator.from_designspace(ds, round_geometry=True)
    return [
        (inst, instantiator.generate_instance(inst))
        for inst in ds.instances
        if _in_range(ds, inst)
    ]


def apply_instance_metadata(
    font: ufoLib2.Font, inst: InstanceDescriptor, weight_class: int
) -> None:
    info = font.info
    info.familyName = inst.familyName
    info.styleName = inst.styleName
    info.openTypeOS2WeightClass = weight_class
    info.postscriptFontName = inst.postScriptFontName
    info.styleMapFamilyName = inst.styleMapFamilyName
    info.styleMapStyleName = inst.styleMapStyleName
    info.postscriptWeightName = _CFF_WEIGHT_NAMES.get(
        cast(str, inst.styleName), info.postscriptWeightName
    )
    if inst.styleName in ("Regular", "Bold"):
        info.openTypeNamePreferredFamilyName = None
        info.openTypeNamePreferredSubfamilyName = None
    else:
        info.openTypeNamePreferredFamilyName = inst.familyName
        info.openTypeNamePreferredSubfamilyName = inst.styleName
