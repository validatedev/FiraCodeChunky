import logging
import shutil
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import ufoLib2
from fontTools.ttLib import TTFont

from fira_code_chunky import WEIGHT_CLASSES, gates, pipeline
from fira_code_chunky.qa import QAError

REAL_AXIS_MAP = [
    (300, 62),
    (400, 84),
    (450, 96),
    (500, 112),
    (600, 132),
    (700, 158),
]


def test_paths(tmp_path):
    paths = pipeline.Paths(tmp_path)

    assert paths.upstream == tmp_path / "build/upstream"
    assert paths.master_dir == tmp_path / "build/master_ufo"
    assert paths.designspace == paths.master_dir / "FiraCodeChunky.designspace"
    assert paths.vf_designspace == paths.master_dir / "FiraCodeChunkyVF.designspace"
    assert paths.instance_dir == tmp_path / "build/instance_ufo"
    assert paths.dist_ttf == tmp_path / "dist/ttf"
    assert paths.dist_otf == tmp_path / "dist/otf"
    assert paths.dist_woff2 == tmp_path / "dist/woff2"
    assert paths.dist_variable == tmp_path / "dist/variable"


def test_convert_upstream_issues_glyphs2ufo_command(tmp_path, fake_runner):
    paths = pipeline.Paths(tmp_path)

    result = pipeline.convert_upstream(paths, fake_runner)

    assert result == paths.designspace
    assert fake_runner.calls == [
        [
            "glyphs2ufo",
            str(paths.upstream / "FiraCode.glyphs"),
            "-m",
            str(paths.master_dir),
            "--designspace-path",
            str(paths.designspace),
            "--write-public-skip-export-glyphs",
            "--generate-GDEF",
        ]
    ]
    assert paths.master_dir.is_dir()


@pytest.mark.parametrize("build_script_text", [None, "fontmake -m source -o ttf"])
def test_prepare_designspace_loads_gates_and_patches(
    micro_dir, tmp_path, monkeypatch, build_script_text
):
    master_dir = tmp_path / "build/master_ufo"
    shutil.copytree(micro_dir, master_dir)
    ds_path = master_dir / "Micro.designspace"
    if build_script_text is not None:
        script = tmp_path / "build/upstream/script/build.sh"
        script.parent.mkdir(parents=True)
        script.write_text(build_script_text)
    seen = []
    real_gate_report = gates.gate_report

    def capture_gate_report(ds, text):
        seen.append(text)
        return real_gate_report(ds, text)

    monkeypatch.setattr(pipeline.gates, "gate_report", capture_gate_report)

    ds = pipeline.prepare_designspace(ds_path)

    assert seen == [build_script_text or ""]
    assert all(source.font is not None for source in ds.sources)
    assert [instance.styleName for instance in ds.instances] == [
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
    ]
    assert [instance.location["Weight"] for instance in ds.instances] == [
        350,
        450,
        550,
        650,
        750,
    ]
    # GDEF categories applied so spacing accents cannot become mark-classed.
    for source in ds.sources:
        font = cast(ufoLib2.Font, source.font)
        cats = font.lib.get("public.openTypeCategories", {})
        assert cats.get("acutecomb") == "mark"


def test_bake_all_five_styles(micro_ds):
    baked = pipeline.bake_all(micro_ds)

    assert [style for style, _font in baked] == [
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
    ]
    fonts = dict(baked)
    assert fonts["Bold"].info.openTypeOS2WeightClass == 700
    xs = sorted({point.x for point in fonts["Bold"]["I"].contours[0].points})
    assert xs == [235, 365]
    # Bold is extrapolated without lib copy; categories must still be present.
    assert fonts["Bold"].lib.get("public.openTypeCategories", {}).get("acutecomb") == (
        "mark"
    )


def test_bake_all_uses_mapped_target_and_actual_master_locations(micro_ds, monkeypatch):
    axis = micro_ds.axes[0]
    axis.minimum = 300
    axis.maximum = 700
    axis.default = 300
    axis.map = list(REAL_AXIS_MAP)
    source_locations = [62, 158]
    for source, location in zip(micro_ds.sources, source_locations, strict=True):
        source.location["Weight"] = location
    instance_locations = [62, 84, 96, 112, 132, 158]
    for instance, location in zip(micro_ds.instances, instance_locations, strict=True):
        instance.location["Weight"] = location
    seen_t = []
    real_extrapolate = pipeline.extrapolate.extrapolate_font

    def capture_extrapolate(light, bold, t):
        seen_t.append(t)
        return real_extrapolate(light, bold, t)

    monkeypatch.setattr(pipeline.extrapolate, "extrapolate_font", capture_extrapolate)
    pipeline.patch.make_chunky(micro_ds)

    baked = pipeline.bake_all(micro_ds)

    assert [instance.location["Weight"] for instance in micro_ds.instances] == [
        73,
        96,
        122,
        145,
        171,
    ]
    assert seen_t == [pytest.approx(109 / 96)]
    assert [style for style, _font in baked] == list(WEIGHT_CLASSES)


def test_compile_commands_sequence(tmp_path):
    paths = pipeline.Paths(tmp_path)

    commands = pipeline.compile_commands(paths, ["Regular"], ["--flatten-components"])

    name = "FiraCodeChunky-Regular"
    ufo = paths.instance_dir / f"{name}.ufo"
    raw_ttf = paths.instance_dir / f"{name}.ttf"
    ttf = paths.dist_ttf / f"{name}.ttf"
    otf = paths.dist_otf / f"{name}.otf"
    assert commands == [
        [
            "fontmake",
            "-u",
            str(ufo),
            "-o",
            "ttf",
            "--output-dir",
            str(paths.instance_dir),
            "--flatten-components",
        ],
        [
            "fontmake",
            "-u",
            str(ufo),
            "-o",
            "otf",
            "--output-dir",
            str(paths.dist_otf),
            "--flatten-components",
        ],
        [sys.executable, "-m", "ttfautohint", "--no-info", str(raw_ttf), str(ttf)],
        ["otfautohint", "--overwrite", str(otf)],
        ["gftools", "fix-font", "-o", str(ttf), str(ttf)],
        ["gftools", "fix-font", "-o", str(otf), str(otf)],
    ]


def test_compile_commands_skips_otfautohint_when_unavailable(tmp_path):
    paths = pipeline.Paths(tmp_path)

    commands = pipeline.compile_commands(paths, ["Regular"], [], otf_hint=False)

    assert ["otfautohint", "--overwrite", str(paths.dist_otf / "x")] not in commands
    assert not any(argv[0] == "otfautohint" for argv in commands)
    # ttfautohint still runs for the TTF.
    assert any("ttfautohint" in argv for argv in commands)


def test_build_statics_runs_commands_and_finalizes_outputs(
    tmp_path, fake_runner, monkeypatch
):
    paths = pipeline.Paths(tmp_path)
    finalized = []
    monkeypatch.setattr(
        pipeline,
        "finalize_binary",
        lambda path, style: finalized.append((path, style)),
    )
    monkeypatch.setattr(pipeline.shutil, "which", lambda tool: "/usr/bin/otfautohint")

    result = pipeline.build_statics(paths, fake_runner, ["--flatten-components"])

    assert fake_runner.calls == pipeline.compile_commands(
        paths, list(WEIGHT_CLASSES), ["--flatten-components"], otf_hint=True
    )
    assert result == [
        paths.dist_ttf / f"FiraCodeChunky-{style}.ttf" for style in WEIGHT_CLASSES
    ]
    assert finalized == [
        item
        for style in WEIGHT_CLASSES
        for item in [
            (paths.dist_ttf / f"FiraCodeChunky-{style}.ttf", style),
            (paths.dist_otf / f"FiraCodeChunky-{style}.otf", style),
        ]
    ]
    assert paths.instance_dir.is_dir()
    assert paths.dist_ttf.is_dir()
    assert paths.dist_otf.is_dir()


def test_build_statics_skips_otf_hint_when_tool_absent(
    tmp_path, fake_runner, monkeypatch
):
    paths = pipeline.Paths(tmp_path)
    monkeypatch.setattr(pipeline, "finalize_binary", lambda path, style: None)
    monkeypatch.setattr(pipeline.shutil, "which", lambda tool: None)

    pipeline.build_statics(paths, fake_runner, [])

    assert not any(argv[0] == "otfautohint" for argv in fake_runner.calls)
    assert fake_runner.calls == pipeline.compile_commands(
        paths, list(WEIGHT_CLASSES), [], otf_hint=False
    )


def test_finalize_binary_pins_and_checks(micro_ttf_path, tmp_path):
    path = tmp_path / "FiraCodeChunky-Regular.ttf"
    shutil.copy(micro_ttf_path, path)

    pipeline.finalize_binary(path, "Regular")

    font = TTFont(path)
    os2 = cast(Any, font["OS/2"])
    post = cast(Any, font["post"])
    assert os2.usWeightClass == 400
    assert os2.usWidthClass == 5
    assert post.isFixedPitch == 1


def test_build_woff2(micro_ttf_path, tmp_path):
    output = pipeline.build_woff2([micro_ttf_path], tmp_path)

    assert output == [tmp_path / micro_ttf_path.with_suffix(".woff2").name]
    assert output[0].exists()
    assert TTFont(output[0]).flavor == "woff2"


def test_run_build_orchestrates_success(tmp_path, monkeypatch, fake_runner):
    paths = pipeline.Paths(tmp_path)
    build_script = paths.upstream / "script/build.sh"
    build_script.parent.mkdir(parents=True)
    build_script.write_text(
        "fontmake -m source.designspace -o ttf --flatten-components"
    )
    ds = object()
    fonts = [("Regular", ufoLib2.Font())]
    ttf_paths = [paths.dist_ttf / "FiraCodeChunky-Regular.ttf"]
    vf_path = paths.dist_variable / "FiraCodeChunky-VF.ttf"
    calls = []
    monkeypatch.setattr(
        pipeline,
        "convert_upstream",
        lambda actual_paths, runner: (
            calls.append(("convert", actual_paths, runner)) or paths.designspace
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "prepare_designspace",
        lambda ds_path: calls.append(("prepare", ds_path)) or ds,
    )
    monkeypatch.setattr(
        pipeline,
        "bake_all",
        lambda actual_ds: calls.append(("bake", actual_ds)) or fonts,
    )

    def fake_build_statics(actual_paths, runner, flags):
        calls.append(("statics", actual_paths, runner, list(flags)))
        assert (paths.instance_dir / "FiraCodeChunky-Regular.ufo").is_dir()
        return ttf_paths

    monkeypatch.setattr(pipeline, "build_statics", fake_build_statics)
    monkeypatch.setattr(
        pipeline,
        "build_woff2",
        lambda paths_arg, out_dir: (
            calls.append(("woff2", list(paths_arg), out_dir)) or []
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "build_variable",
        lambda actual_paths, runner, flags: (
            calls.append(("variable", actual_paths, runner, list(flags))) or vf_path
        ),
    )
    runner = fake_runner

    assert pipeline.run_build(tmp_path, runner) == 0
    assert calls == [
        ("convert", paths, runner),
        ("prepare", paths.designspace),
        ("bake", ds),
        ("statics", paths, runner, ["--flatten-components"]),
        ("woff2", ttf_paths, paths.dist_woff2),
        ("variable", paths, runner, ["--flatten-components"]),
        ("woff2", [vf_path], paths.dist_woff2),
    ]


def test_build_variable_issues_fontmake_then_fix(tmp_path, fake_runner, monkeypatch):
    paths = pipeline.Paths(tmp_path)
    built = []
    monkeypatch.setattr(
        pipeline.variable,
        "build_vf_designspace",
        lambda instance_dir, out_path: built.append((instance_dir, out_path)),
    )
    monkeypatch.setattr(
        pipeline.variable, "finalize_vf", lambda path: built.append(("finalize", path))
    )

    vf = pipeline.build_variable(paths, fake_runner, ["--flatten-components"])

    assert vf == paths.dist_variable / "FiraCodeChunky-VF.ttf"
    assert built == [
        (paths.instance_dir, paths.vf_designspace),
        ("finalize", vf),
    ]
    assert fake_runner.calls == [
        [
            "fontmake",
            "-m",
            str(paths.vf_designspace),
            "-o",
            "variable",
            "--output-dir",
            str(paths.dist_variable),
            "--flatten-components",
        ],
        ["gftools", "fix-font", "-o", str(vf), str(vf)],
    ]
    assert paths.dist_variable.is_dir()


def test_place_vf_renames_fontmake_output(tmp_path):
    out_dir = tmp_path / "variable"
    out_dir.mkdir()
    produced = out_dir / "FiraCodeChunkyVF-VF.ttf"
    produced.write_bytes(b"font")

    vf = pipeline._place_vf(out_dir)

    assert vf == out_dir / "FiraCodeChunky-VF.ttf"
    assert vf.read_bytes() == b"font"
    assert not produced.exists()


def test_place_vf_keeps_correctly_named_output(tmp_path):
    out_dir = tmp_path / "variable"
    out_dir.mkdir()
    target = out_dir / "FiraCodeChunky-VF.ttf"
    target.write_bytes(b"font")

    assert pipeline._place_vf(out_dir) == target
    assert target.read_bytes() == b"font"


def test_build_variable_renames_and_finalizes(tmp_path, monkeypatch):
    paths = pipeline.Paths(tmp_path)
    monkeypatch.setattr(
        pipeline.variable, "build_vf_designspace", lambda instance_dir, out: None
    )
    finalized = []
    monkeypatch.setattr(
        pipeline.variable, "finalize_vf", lambda path: finalized.append(path)
    )

    class ProducingRunner:
        def __init__(self):
            self.calls = []

        def run(self, argv, cwd=None):
            self.calls.append(list(argv))
            if argv[0] == "fontmake":
                paths.dist_variable.mkdir(parents=True, exist_ok=True)
                (paths.dist_variable / "FiraCodeChunkyVF-VF.ttf").write_bytes(b"vf")
            return None

    runner = ProducingRunner()
    vf = pipeline.build_variable(paths, runner, [])

    assert vf == paths.dist_variable / "FiraCodeChunky-VF.ttf"
    assert vf.read_bytes() == b"vf"
    assert finalized == [vf]
    assert runner.calls[-1] == ["gftools", "fix-font", "-o", str(vf), str(vf)]


def test_run_build_orchestrates_variable_after_statics(
    tmp_path, monkeypatch, fake_runner
):
    paths = pipeline.Paths(tmp_path)
    order = []
    monkeypatch.setattr(pipeline, "convert_upstream", lambda p, r: paths.designspace)
    monkeypatch.setattr(pipeline, "prepare_designspace", lambda ds_path: object())
    monkeypatch.setattr(pipeline, "bake_all", lambda ds: [])
    monkeypatch.setattr(
        pipeline,
        "build_statics",
        lambda p, r, f: order.append("statics") or [],
    )
    monkeypatch.setattr(
        pipeline,
        "build_variable",
        lambda p, r, f: order.append("variable") or (paths.dist_variable / "x.ttf"),
    )
    monkeypatch.setattr(
        pipeline, "build_woff2", lambda paths_arg, out_dir: order.append("woff2")
    )

    assert pipeline.run_build(tmp_path, fake_runner) == 0
    assert order == ["statics", "woff2", "variable", "woff2"]


def test_run_build_returns_1_on_runner_failure(tmp_path, fake_runner, caplog):
    fake_runner.fail_on.add("glyphs2ufo")

    with caplog.at_level(logging.ERROR):
        result = pipeline.run_build(tmp_path, fake_runner)

    assert result == 1
    assert "build failed" in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        gates.GateError("gate"),
        QAError("qa"),
        # Fix 2: a build-input failure (e.g. incompatible masters) must exit
        # cleanly (1) like the other validation errors, not propagate as an
        # uncaught exception.
        pipeline.extrapolate.IncompatibleMastersError("glyph sets differ"),
    ],
)
def test_run_build_returns_1_on_validation_failure(
    tmp_path, fake_runner, monkeypatch, error
):
    monkeypatch.setattr(pipeline, "convert_upstream", lambda paths, runner: Path())
    monkeypatch.setattr(
        pipeline, "prepare_designspace", lambda ds_path: (_ for _ in ()).throw(error)
    )

    assert pipeline.run_build(tmp_path, fake_runner) == 1
