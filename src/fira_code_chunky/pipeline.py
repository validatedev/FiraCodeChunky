"""Static-font build pipeline orchestration."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.ttLib import TTFont

from fira_code_chunky import (
    DESIGN_SHIFT,
    FAMILY_NAME,
    WEIGHT_CLASSES,
    bake,
    commands,
    extrapolate,
    gates,
    metadata,
    patch,
    qa,
)
from fira_code_chunky.gates import GateError
from fira_code_chunky.qa import QAError
from fira_code_chunky.runner import Runner, RunnerError


@dataclass(frozen=True)
class Paths:
    """Repository-relative inputs, work directories, and build outputs."""

    root: Path

    @property
    def upstream(self) -> Path:
        return self.root / "build/upstream"

    @property
    def master_dir(self) -> Path:
        return self.root / "build/master_ufo"

    @property
    def designspace(self) -> Path:
        return self.master_dir / "FiraCodeChunky.designspace"

    @property
    def instance_dir(self) -> Path:
        return self.root / "build/instance_ufo"

    @property
    def dist_ttf(self) -> Path:
        return self.root / "dist/ttf"

    @property
    def dist_otf(self) -> Path:
        return self.root / "dist/otf"

    @property
    def dist_woff2(self) -> Path:
        return self.root / "dist/woff2"

    @property
    def dist_vf(self) -> Path:
        return self.root / "dist/vf"


def _build_script_text(ds_path: Path) -> str:
    build_script = ds_path.parent.parent / "upstream/script/build.sh"
    return build_script.read_text() if build_script.exists() else ""


def convert_upstream(paths: Paths, runner: Runner) -> Path:
    """Convert the upstream Glyphs source into master UFOs and a designspace."""
    paths.master_dir.mkdir(parents=True, exist_ok=True)
    runner.run(
        commands.glyphs2ufo_command(
            paths.upstream / "FiraCode.glyphs",
            paths.master_dir,
            paths.designspace,
        )
    )
    return paths.designspace


def prepare_designspace(ds_path: Path) -> DesignSpaceDocument:
    """Load, validate, and patch an upstream designspace in memory."""
    ds = DesignSpaceDocument.fromfile(ds_path)
    ds.loadSourceFonts(ufoLib2.Font.open)
    gates.gate_report(ds, _build_script_text(ds_path))
    patch.make_chunky(ds)
    return ds


def bake_all(ds: DesignSpaceDocument) -> list[tuple[str, ufoLib2.Font]]:
    """Bake four interior instances and the map-aware extrapolated Bold."""
    if any(instance.styleName == "Retina" for instance in ds.instances):
        patch.make_chunky(ds)

    baked: list[tuple[str, ufoLib2.Font]] = []
    for instance, font in bake.bake_interior_instances(ds):
        style = cast(str, instance.styleName)
        bake.apply_instance_metadata(font, instance, WEIGHT_CLASSES[style])
        baked.append((style, font))

    name = patch.axis_name(ds)
    sources = sorted(ds.sources, key=lambda source: source.location[name])
    light_source, bold_source = sources[0], sources[-1]
    light_location = light_source.location[name]
    bold_location = bold_source.location[name]
    axis_map = next(axis.map for axis in ds.axes if axis.tag == "wght")
    target = patch.piecewise_design(
        axis_map, WEIGHT_CLASSES["Bold"] + DESIGN_SHIFT
    )
    t = (target - light_location) / (bold_location - light_location)
    bold_font = extrapolate.extrapolate_font(
        cast(ufoLib2.Font, light_source.font),
        cast(ufoLib2.Font, bold_source.font),
        t,
    )
    bold_instance = next(
        instance for instance in ds.instances if instance.styleName == "Bold"
    )
    bake.apply_instance_metadata(
        bold_font, bold_instance, WEIGHT_CLASSES["Bold"]
    )
    baked.append(("Bold", bold_font))
    return baked


def _binary_paths(paths: Paths, style: str) -> tuple[Path, Path, Path, Path]:
    stem = f"FiraCodeChunky-{style.replace(' ', '')}"
    return (
        paths.instance_dir / f"{stem}.ufo",
        paths.instance_dir / f"{stem}.ttf",
        paths.dist_ttf / f"{stem}.ttf",
        paths.dist_otf / f"{stem}.otf",
    )


def compile_commands(
    paths: Paths, styles: Sequence[str], flags: Sequence[str]
) -> list[list[str]]:
    """Build the argv sequence for static compilation and post-processing."""
    argv: list[list[str]] = []
    for style in styles:
        ufo, raw_ttf, ttf, otf = _binary_paths(paths, style)
        argv.extend(
            [
                commands.fontmake_ufo_command(
                    ufo, "ttf", paths.instance_dir, flags
                ),
                commands.fontmake_ufo_command(ufo, "otf", paths.dist_otf, flags),
                commands.ttfautohint_command(raw_ttf, ttf),
                commands.otfautohint_command(otf),
                commands.gftools_fix_command(ttf),
                commands.gftools_fix_command(otf),
            ]
        )
    return argv


def finalize_binary(path: Path, style: str) -> None:
    """Pin required metadata, assert it, and persist the binary."""
    with TTFont(path) as font:
        metadata.pin_all(font, FAMILY_NAME, style, WEIGHT_CLASSES[style])
        qa.assert_static_metadata(font, FAMILY_NAME, style, WEIGHT_CLASSES[style])
        font.save(path)


def build_statics(
    paths: Paths, runner: Runner, flags: Sequence[str]
) -> list[Path]:
    """Compile, hint, fix, and finalize all five static styles."""
    for directory in (paths.instance_dir, paths.dist_ttf, paths.dist_otf):
        directory.mkdir(parents=True, exist_ok=True)
    styles = list(WEIGHT_CLASSES)
    for argv in compile_commands(paths, styles, flags):
        runner.run(argv)
    ttf_paths: list[Path] = []
    for style in styles:
        _ufo, _raw_ttf, ttf, otf = _binary_paths(paths, style)
        finalize_binary(ttf, style)
        finalize_binary(otf, style)
        ttf_paths.append(ttf)
    return ttf_paths


def build_woff2(ttf_paths: Sequence[Path], out_dir: Path) -> list[Path]:
    """Encode finalized TTFs as WOFF2 using fontTools."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for path in ttf_paths:
        output = out_dir / path.with_suffix(".woff2").name
        with TTFont(path, flavor=None) as font:
            font.flavor = "woff2"
            font.save(output)
        outputs.append(output)
    return outputs


def run_build(root: Path, runner: Runner) -> int:
    """Run the complete static build, returning a process-style exit code."""
    paths = Paths(root)
    try:
        ds_path = convert_upstream(paths, runner)
        ds = prepare_designspace(ds_path)
        baked = bake_all(ds)
        paths.instance_dir.mkdir(parents=True, exist_ok=True)
        for style, font in baked:
            font.save(paths.instance_dir / f"FiraCodeChunky-{style}.ufo")
        flags = gates.extract_fontmake_flags(_build_script_text(ds_path))
        ttf_paths = build_statics(paths, runner, flags)
        build_woff2(ttf_paths, paths.dist_woff2)
    except (GateError, QAError, RunnerError) as error:
        logging.getLogger(__name__).error("build failed: %s", error)
        return 1
    return 0
