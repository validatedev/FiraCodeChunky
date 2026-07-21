"""Pre-build checks for assumptions inherited from upstream Fira Code."""

from __future__ import annotations

import shlex
from itertools import pairwise

from fontTools.designspaceLib import DesignSpaceDocument

CUSTOM_PARAMETERS_KEY = "com.schriftgestaltung.customParameters"
WEIGHT_CLASS_KEYS = {"weightClass", "openTypeOS2WeightClass"}
FONTMAKE_OPTIONS_WITH_VALUES = {
    "-g",
    "-m",
    "-o",
    "-u",
    "--output-dir",
    "--output-path",
}
FONTMAKE_OPTIONS_WITH_OPTIONAL_VALUES = {"-i", "--interpolate"}


class GateError(RuntimeError):
    """Raised when an upstream assumption makes the build unsafe."""


def _weight_axis_map(ds: DesignSpaceDocument) -> list[tuple[float, float]]:
    for axis in ds.axes:
        if axis.tag == "wght":
            return list(axis.map)
    return []


def _validate_weight_axis_map(ds: DesignSpaceDocument) -> list[tuple[float, float]]:
    map_ = _weight_axis_map(ds)
    if not map_:
        return map_
    if len(map_) < 2:
        raise GateError("wght axis map must contain at least 2 entries")
    if any(right[0] <= left[0] for left, right in pairwise(map_)):
        raise GateError("wght axis map user coordinates must be strictly increasing")
    if any(right[1] <= left[1] for left, right in pairwise(map_)):
        raise GateError("wght axis map design coordinates must be strictly increasing")

    axis_name = next(axis.name for axis in ds.axes if axis.tag == "wght")
    design_min, design_max = map_[0][1], map_[-1][1]
    for source in ds.sources:
        location = source.location.get(axis_name)
        if location is not None and not design_min <= location <= design_max:
            raise GateError(
                f"master location {location} is outside mapped design range "
                f"{design_min}..{design_max}"
            )
    return map_


def weight_class_key_present(ds: DesignSpaceDocument) -> bool:
    """Return whether every instance has an explicit OS/2 weight-class hint."""
    return all(
        "openTypeOS2WeightClass" in instance.lib
        or any(
            name in WEIGHT_CLASS_KEYS
            for name, _value in instance.lib.get(CUSTOM_PARAMETERS_KEY, [])
        )
        for instance in ds.instances
    )


def axis_is_linear(ds: DesignSpaceDocument) -> bool:
    """Return whether every axis has no user-to-design coordinate map."""
    return all(not axis.map for axis in ds.axes)


def extract_fontmake_flags(build_script_text: str) -> list[str]:
    """Extract order-preserving unique flags from upstream fontmake commands."""
    flags: list[str] = []
    for line in build_script_text.splitlines():
        stripped = line.strip()
        try:
            tokens = shlex.split(stripped, posix=True)
        except ValueError:
            tokens = stripped.split()
        if not tokens or tokens[0] != "fontmake":
            continue

        rest = tokens[1:]
        skip_next = False
        for index, token in enumerate(rest):
            if skip_next:
                skip_next = False
                continue
            if token in FONTMAKE_OPTIONS_WITH_VALUES:
                skip_next = True
                continue
            if token in FONTMAKE_OPTIONS_WITH_OPTIONAL_VALUES:
                next_token = rest[index + 1] if index + 1 < len(rest) else None
                if next_token is not None and not next_token.startswith("-"):
                    skip_next = True
                continue
            if token not in flags:
                flags.append(token)
    return flags


def gate_report(ds: DesignSpaceDocument, build_script_text: str) -> dict[str, object]:
    """Return upstream gate results after validating any weight-axis map."""
    axis_linear = axis_is_linear(ds)
    axis_map = _validate_weight_axis_map(ds)

    return {
        "weight_class_key": weight_class_key_present(ds),
        "axis_linear": axis_linear,
        "axis_map": axis_map,
        "fontmake_flags": extract_fontmake_flags(build_script_text),
    }
