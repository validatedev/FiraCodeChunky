from pathlib import Path

import pytest

from fira_code_chunky import commands as c


def test_glyphs2ufo():
    argv = c.glyphs2ufo_command(Path("F.glyphs"), Path("m"), Path("d.designspace"))
    assert argv[0] == "glyphs2ufo"
    assert "F.glyphs" in argv
    assert "--designspace-path" in argv


def test_fontmake_ufo_ttf():
    argv = c.fontmake_ufo_command(
        Path("R.ufo"), "ttf", Path("out"), ["--flatten-components"]
    )
    assert argv == [
        "fontmake",
        "-u",
        "R.ufo",
        "-o",
        "ttf",
        "--output-dir",
        "out",
        "--flatten-components",
    ]


def test_fontmake_ufo_rejects_bad_format():
    with pytest.raises(ValueError, match="woff"):
        c.fontmake_ufo_command(Path("R.ufo"), "woff", Path("out"))


def test_fontmake_variable():
    argv = c.fontmake_variable_command(Path("vf.designspace"), Path("out"))
    assert argv == [
        "fontmake",
        "-m",
        "vf.designspace",
        "-o",
        "variable",
        "--output-dir",
        "out",
    ]


def test_ttfautohint_and_otfautohint_and_gftools():
    assert c.ttfautohint_command(Path("a.ttf"), Path("b.ttf"))[0] == "ttfautohint"
    assert c.otfautohint_command(Path("a.otf"))[0] == "otfautohint"
    assert c.gftools_fix_command(Path("a.ttf")) == [
        "gftools",
        "fix-font",
        "-o",
        "a.ttf",
        "a.ttf",
    ]
