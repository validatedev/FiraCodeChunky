"""Pure designspace transformations: Fira Code -> Fira Code Chunky."""

from __future__ import annotations

from collections.abc import Sequence

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument

from fira_code_chunky import DESIGN_SHIFT, FAMILY_NAME, PS_FAMILY

RIBBI = {"Regular": "regular", "Bold": "bold"}
AxisMap = Sequence[tuple[float, float]]


def _piecewise(map_: AxisMap, value: float, input_index: int) -> float:
    if not map_:
        return value

    for index, right in enumerate(map_[1:], start=1):
        if value <= right[input_index]:
            left = map_[index - 1]
            break
    else:
        left, right = map_[-2:]

    output_index = 1 - input_index
    input_span = right[input_index] - left[input_index]
    output_span = right[output_index] - left[output_index]
    return left[output_index] + (value - left[input_index]) * output_span / input_span


def piecewise_design(map_: AxisMap, user: float) -> float:
    """Convert a user weight to its mapped design coordinate."""
    return _piecewise(map_, user, 0)


def piecewise_user(map_: AxisMap, design: float) -> float:
    """Convert a design coordinate to its mapped user weight."""
    return _piecewise(map_, design, 1)


def axis_name(ds: DesignSpaceDocument) -> str:
    for axis in ds.axes:
        if axis.tag == "wght":
            assert axis.name is not None
            return axis.name
    raise ValueError("no wght axis in designspace")


def drop_instance(ds: DesignSpaceDocument, style_name: str) -> None:
    matches = [i for i in ds.instances if i.styleName == style_name]
    if not matches:
        raise ValueError(f"no instance named {style_name!r}")
    for inst in matches:
        ds.instances.remove(inst)


def shift_instance_locations(
    ds: DesignSpaceDocument, delta: float = DESIGN_SHIFT
) -> None:
    name = axis_name(ds)
    map_ = next(axis.map for axis in ds.axes if axis.tag == "wght")
    top = 0.0
    for inst in ds.instances:
        inst.location = dict(inst.location)
        user = piecewise_user(map_, inst.location[name])
        design = piecewise_design(map_, user + delta)
        inst.location[name] = design
        top = max(top, design)
    for axis in ds.axes:
        if (
            isinstance(axis, AxisDescriptor)
            and axis.name == name
            and axis.maximum is not None
            and axis.maximum < top
        ):
            axis.maximum = top


def rename_family(ds: DesignSpaceDocument, new_family: str = FAMILY_NAME) -> None:
    for inst in ds.instances:
        style = inst.styleName
        assert style is not None
        inst.familyName = new_family
        inst.postScriptFontName = f"{PS_FAMILY}-{style.replace(' ', '')}"
        if style in RIBBI:
            inst.styleMapFamilyName = new_family
            inst.styleMapStyleName = RIBBI[style]
        else:
            inst.styleMapFamilyName = f"{new_family} {style}"
            inst.styleMapStyleName = "regular"


def make_chunky(ds: DesignSpaceDocument) -> None:
    drop_instance(ds, "Retina")
    shift_instance_locations(ds)
    rename_family(ds)
