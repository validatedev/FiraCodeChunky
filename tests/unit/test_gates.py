import pytest
from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    SourceDescriptor,
)

from fira_code_chunky.gates import (
    GateError,
    axis_is_linear,
    extract_fontmake_flags,
    gate_report,
    weight_class_key_present,
)

BUILD_SH = """
#!/bin/bash
fontmake -g FiraCode.glyphs -o ttf --output-dir distr/ttf --flatten-components --filter DecomposeTransformedComponentsFilter
fontmake -m FiraCode.designspace -o variable --output-dir distr/vf --flatten-components
fontmake -u FiraCode-Regular.ufo -o otf --output-dir distr/otf --filter DecomposeTransformedComponentsFilter
fontmaker --keep-this-out
echo fontmake --also-keep-this-out
"""

UPSTREAM_BUILD_SH = """
#!/bin/bash
fontmake -g "FiraCode.glyphs" -o ttf --output-path "distr/ttf/FiraCode-Regular.ttf" -i ".* Regular" --flatten-components
"""

BARE_INTERPOLATE_BUILD_SH = """
fontmake -g F.glyphs -o ttf -i --flatten-components
"""

CUSTOM_PARAMETERS_KEY = "com.schriftgestaltung.customParameters"
REAL_AXIS_MAP = [
    (300, 62),
    (400, 84),
    (450, 96),
    (500, 112),
    (600, 132),
    (700, 158),
]


def mapped_designspace(
    map_=REAL_AXIS_MAP, master_locations=(62, 158)
) -> DesignSpaceDocument:
    ds = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.tag = "wght"
    axis.name = "Weight"
    axis.minimum = 62
    axis.maximum = 158
    axis.default = 84
    axis.map = list(map_)
    ds.addAxis(axis)

    for location in master_locations:
        source = SourceDescriptor()
        source.location = {"Weight": location}
        ds.addSource(source)
    return ds


def test_axis_linear_true_when_axis_map_is_absent(micro_ds):
    assert axis_is_linear(micro_ds)


def test_axis_linear_false_when_axis_map_is_present(micro_ds):
    micro_ds.axes[0].map = [(300, 300), (400, 380), (700, 700)]

    assert not axis_is_linear(micro_ds)


def test_weight_class_key_absent_on_fixture(micro_ds):
    assert not weight_class_key_present(micro_ds)


@pytest.mark.parametrize("key", ["weightClass", "openTypeOS2WeightClass"])
def test_weight_class_custom_parameter_present_on_every_instance(micro_ds, key):
    for instance in micro_ds.instances:
        instance.lib[CUSTOM_PARAMETERS_KEY] = [[key, 450]]

    assert weight_class_key_present(micro_ds)


def test_weight_class_fontinfo_key_present_on_every_instance(micro_ds):
    for instance in micro_ds.instances:
        instance.lib["openTypeOS2WeightClass"] = 450

    assert weight_class_key_present(micro_ds)


def test_weight_class_key_must_be_present_on_every_instance(micro_ds):
    micro_ds.instances[0].lib[CUSTOM_PARAMETERS_KEY] = [["weightClass", 300]]

    assert not weight_class_key_present(micro_ds)


def test_extract_fontmake_flags_skips_inputs_outputs_and_other_commands():
    assert extract_fontmake_flags(BUILD_SH) == [
        "--flatten-components",
        "--filter",
        "DecomposeTransformedComponentsFilter",
    ]


def test_extract_fontmake_flags_handles_quoted_output_path_and_instance_pattern():
    assert extract_fontmake_flags(UPSTREAM_BUILD_SH) == ["--flatten-components"]


def test_extract_fontmake_flags_treats_bare_interpolate_flag_as_valueless():
    assert extract_fontmake_flags(BARE_INTERPOLATE_BUILD_SH) == ["--flatten-components"]


def test_gate_report_accepts_mapped_weight_axis():
    report = gate_report(mapped_designspace(), BUILD_SH)

    assert report["axis_linear"] is False
    assert report["axis_map"] == REAL_AXIS_MAP


def test_gate_report_ignores_map_on_non_weight_axis():
    ds = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.tag = "wdth"
    axis.name = "Width"
    axis.minimum = 75
    axis.maximum = 100
    axis.default = 100
    axis.map = [(75, 70), (100, 100)]
    ds.addAxis(axis)

    report = gate_report(ds, BUILD_SH)

    assert report["axis_linear"] is False
    assert report["axis_map"] == []


@pytest.mark.parametrize(
    ("map_", "message"),
    [
        ([(300, 62)], "at least 2"),
        ([(300, 62), (400, 84), (350, 96)], "user coordinates"),
        ([(300, 62), (300, 84)], "user coordinates"),
        ([(300, 62), (400, 84), (450, 80)], "design coordinates"),
        ([(300, 62), (400, 62)], "design coordinates"),
    ],
)
def test_gate_report_rejects_malformed_axis_maps(map_, message):
    with pytest.raises(GateError, match=message):
        gate_report(mapped_designspace(map_=map_, master_locations=()), BUILD_SH)


@pytest.mark.parametrize("master_location", [61, 159])
def test_gate_report_rejects_masters_outside_mapped_design_range(master_location):
    with pytest.raises(GateError, match=r"master.*mapped design range"):
        gate_report(mapped_designspace(master_locations=(master_location,)), BUILD_SH)


def test_gate_report_returns_all_informational_results(micro_ds):
    assert gate_report(micro_ds, BUILD_SH) == {
        "weight_class_key": False,
        "axis_linear": True,
        "axis_map": [],
        "fontmake_flags": [
            "--flatten-components",
            "--filter",
            "DecomposeTransformedComponentsFilter",
        ],
    }


def test_extract_fontmake_flags_falls_back_on_unbalanced_quotes():
    text = 'fontmake -g F.glyphs -o ttf --flatten-components "unbalanced\n'
    assert extract_fontmake_flags(text) == ["--flatten-components", '"unbalanced']
