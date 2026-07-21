"""Pre-build checks for assumptions inherited from upstream Fira Code."""

from __future__ import annotations

from fontTools.designspaceLib import DesignSpaceDocument

CUSTOM_PARAMETERS_KEY = "com.schriftgestaltung.customParameters"
WEIGHT_CLASS_KEYS = {"weightClass", "openTypeOS2WeightClass"}
FONTMAKE_OPTIONS_WITH_VALUES = {"-g", "-m", "-o", "-u", "--output-dir"}


class GateError(RuntimeError):
    """Raised when an upstream assumption makes the build unsafe."""


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
        tokens = line.strip().split()
        if not tokens or tokens[0] != "fontmake":
            continue

        skip_next = False
        for token in tokens[1:]:
            if skip_next:
                skip_next = False
                continue
            if token in FONTMAKE_OPTIONS_WITH_VALUES:
                skip_next = True
                continue
            if token not in flags:
                flags.append(token)
    return flags


def gate_report(ds: DesignSpaceDocument, build_script_text: str) -> dict[str, object]:
    """Return upstream gate results, stopping if any axis has a map."""
    axis_linear = axis_is_linear(ds)
    if not axis_linear:
        raise GateError("designspace axes must be linear; found an axis map")

    return {
        "weight_class_key": weight_class_key_present(ds),
        "axis_linear": axis_linear,
        "fontmake_flags": extract_fontmake_flags(build_script_text),
    }
