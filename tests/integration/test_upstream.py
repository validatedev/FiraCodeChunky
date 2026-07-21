import json
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
    # Upstream's wght axis is piecewise, not linear; gate_report carries the
    # user->design map through instead of raising.
    assert report["axis_linear"] is False
    assert report["axis_map"] == [
        (300.0, 62.0),
        (400.0, 84.0),
        (450.0, 96.0),
        (500.0, 112.0),
        (600.0, 132.0),
        (700.0, 158.0),
    ]
    styles = [i.styleName for i in ds.instances]
    assert "Retina" in styles
    assert "Regular" in styles

    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)
    with (build_dir / "gate_report.json").open("w") as f:
        # json serializes tuples (e.g. axis_map entries) as arrays natively.
        json.dump(report, f, indent=2)
