import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

_spec = importlib.util.spec_from_file_location("build_nerd", SCRIPTS / "build_nerd.py")
assert _spec is not None and _spec.loader is not None
build_nerd = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = build_nerd
_spec.loader.exec_module(build_nerd)


def test_variant_ids_are_exactly_plain_mono_propo():
    assert {vid for vid, *_ in build_nerd.VARIANTS} == {"plain", "mono", "propo"}


def test_common_flags_exact():
    assert build_nerd.COMMON_FLAGS == ("--complete", "--makegroups", "1", "--quiet")


def test_variant_command_flags():
    fontforge = "fontforge"
    src = Path("dist/ttf/FiraCodeChunky-Regular.ttf")
    out_dir = Path("dist/nerd")

    for vid, _family, _stem_infix, width_flags in build_nerd.VARIANTS:
        cmd = build_nerd.patcher_command(fontforge, src, out_dir, width_flags)

        for flag in build_nerd.COMMON_FLAGS:
            assert flag in cmd, f"{vid}: missing common flag {flag!r} in {cmd}"

        assert "--outputdir" in cmd, f"{vid}: missing --outputdir in {cmd}"
        assert cmd[-1] == str(src), f"{vid}: command does not end with src path: {cmd}"

        if vid == "mono":
            assert "--mono" in cmd
            assert "--variable-width-glyphs" not in cmd
        elif vid == "propo":
            assert "--variable-width-glyphs" in cmd
            assert "--mono" not in cmd
        elif vid == "plain":
            assert "--mono" not in cmd
            assert "--variable-width-glyphs" not in cmd
        else:
            raise AssertionError(f"unexpected variant id {vid!r}")


def test_patcher_command_is_freshly_built_each_call():
    fontforge = "fontforge"
    src = Path("dist/ttf/FiraCodeChunky-Regular.ttf")
    out_dir = Path("dist/nerd")

    mono_flags = next(wf for vid, _f, _s, wf in build_nerd.VARIANTS if vid == "mono")
    propo_flags = next(wf for vid, _f, _s, wf in build_nerd.VARIANTS if vid == "propo")

    cmd_mono = build_nerd.patcher_command(fontforge, src, out_dir, mono_flags)
    cmd_propo = build_nerd.patcher_command(fontforge, src, out_dir, propo_flags)

    assert "--mono" in cmd_mono
    assert "--mono" not in cmd_propo
    assert "--variable-width-glyphs" in cmd_propo
    assert "--variable-width-glyphs" not in cmd_mono
