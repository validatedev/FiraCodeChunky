from pathlib import Path

import pytest

UPSTREAM = Path("build/upstream")
pytestmark = pytest.mark.integration

requires_upstream = pytest.mark.skipif(
    not UPSTREAM.exists(), reason="run scripts/fetch.sh first"
)


@requires_upstream
def test_upstream_has_glyphs_source():
    assert (UPSTREAM / "FiraCode.glyphs").exists()


@requires_upstream
def test_real_conversion_and_gates(tmp_path):
    import ufoLib2  # noqa: F401
    from fontTools.designspaceLib import DesignSpaceDocument

    from fira_code_chunky import commands, gates
    from fira_code_chunky.runner import SubprocessRunner

    ds_path = tmp_path / "FiraCode.designspace"
    SubprocessRunner().run(
        commands.glyphs2ufo_command(UPSTREAM / "FiraCode.glyphs", tmp_path, ds_path)
    )
    ds = DesignSpaceDocument.fromfile(ds_path)
    # Upstream keeps fontmake invocations split across script/build_ttf.sh and
    # script/build_variable.sh (there is no single script/build.sh); concatenate
    # every script/*.sh so flag extraction covers all of them.
    text = "\n".join(
        script.read_text() for script in sorted((UPSTREAM / "script").glob("*.sh"))
    )
    report = gates.gate_report(ds, text)
    assert report["axis_linear"] is True  # HARD requirement for the whole VF plan
    styles = [i.styleName for i in ds.instances]
    assert "Retina" in styles
    assert "Regular" in styles
