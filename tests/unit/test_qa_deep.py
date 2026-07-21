"""Unit tests for deep QA helpers (hint strip, outline delta, shaping, stems)."""

from __future__ import annotations

import contextlib
import io
import logging
import shutil
from pathlib import Path

import pytest
import ufoLib2
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program

from fira_code_chunky import qa, qa_deep

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "micro"


def _compile_ufo(ufo_path: Path, out_dir: Path) -> Path:
    from fontmake.font_project import FontProject

    previous = logging.root.manager.disable
    try:
        logging.disable(logging.CRITICAL)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            FontProject().run_from_ufos(
                [str(ufo_path)],
                output=("ttf",),
                output_dir=str(out_dir),
            )
    finally:
        logging.disable(previous)
    return next(out_dir.glob("*.ttf"))


def _with_unicodes(src_ufo: Path, dest_ufo: Path) -> Path:
    """Copy a micro UFO and assign Latin unicodes so uharfbuzz can shape text."""
    if dest_ufo.exists():
        shutil.rmtree(dest_ufo)
    shutil.copytree(src_ufo, dest_ufo)
    font = ufoLib2.Font.open(dest_ufo)
    font["I"].unicodes = [0x49]
    font["O"].unicodes = [0x4F]
    font["Iacute"].unicodes = [0xCD]
    font["acutecomb"].unicodes = [0x0301]
    # stem_profile probes "l"; alias the stem glyph under that name.
    font["l"] = font["I"].copy()
    font["l"].unicodes = [0x6C]
    font.save(dest_ufo, overwrite=True)
    return dest_ufo


@pytest.fixture(scope="session")
def micro_light_cmap_ttf_path(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("qa-deep-light")
    ufo = _with_unicodes(FIXTURES / "MicroLight.ufo", root / "MicroLight.ufo")
    return _compile_ufo(ufo, root / "out")


@pytest.fixture(scope="session")
def micro_bold_cmap_ttf_path(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("qa-deep-bold")
    ufo = _with_unicodes(FIXTURES / "MicroBold.ufo", root / "MicroBold.ufo")
    return _compile_ufo(ufo, root / "out")


@pytest.fixture
def micro_light_ttf(micro_light_cmap_ttf_path, tmp_path) -> TTFont:
    path = tmp_path / micro_light_cmap_ttf_path.name
    shutil.copy(micro_light_cmap_ttf_path, path)
    return TTFont(path)


@pytest.fixture
def micro_bold_ttf(micro_bold_cmap_ttf_path, tmp_path) -> TTFont:
    path = tmp_path / micro_bold_cmap_ttf_path.name
    shutil.copy(micro_bold_cmap_ttf_path, path)
    return TTFont(path)


def test_strip_hinting_removes_tables_and_programs(micro_light_ttf):
    from fontTools.ttLib import newTable

    font = micro_light_ttf
    # Inject TrueType hinting tables and a per-glyph program so strip has work.
    font["fpgm"] = newTable("fpgm")
    font["fpgm"].program = Program()
    font["fpgm"].program.fromBytecode(b"\xb0\x00")  # NPUSHB 0
    font["prep"] = newTable("prep")
    font["prep"].program = Program()
    font["prep"].program.fromBytecode(b"\xb0\x00")
    font["cvt "] = newTable("cvt ")
    font["cvt "].values = [100, 200]

    glyph = font["glyf"]["I"]
    glyph.program = Program()
    glyph.program.fromBytecode(b"\xb0\x00\x2f")  # junk bytecode

    qa_deep.strip_hinting(font)

    assert "fpgm" not in font
    assert "prep" not in font
    assert "cvt " not in font
    assert glyph.program.getBytecode() == b""


def test_strip_hinting_noop_when_unhinted(micro_light_ttf):
    font = micro_light_ttf
    for tag in ("fpgm", "prep", "cvt "):
        if tag in font:
            del font[tag]
    qa_deep.strip_hinting(font)  # must not raise
    assert "fpgm" not in font


def test_outline_max_delta_identical_is_zero(micro_light_ttf):
    glyphs = ["I", "O", "Iacute"]
    assert qa_deep.outline_max_delta(micro_light_ttf, micro_light_ttf, glyphs) == 0.0


def test_outline_max_delta_light_vs_bold_positive(micro_light_ttf, micro_bold_ttf):
    delta = qa_deep.outline_max_delta(micro_light_ttf, micro_bold_ttf, ["I"])
    assert delta > 0


def test_outline_max_delta_point_count_mismatch_raises(micro_light_ttf, micro_bold_ttf):
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    # Force a point-count mismatch on Bold "I".
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((10, 0))
    pen.lineTo((10, 10))
    pen.closePath()
    micro_bold_ttf["glyf"]["I"] = pen.glyph()
    with pytest.raises(qa.QAError, match="point count"):
        qa_deep.outline_max_delta(micro_light_ttf, micro_bold_ttf, ["I"])


def test_shaped_advances_io(micro_light_cmap_ttf_path):
    # Micro calt rewrites I' O → Iacute; O remains. Both advance 600.
    advances = qa_deep.shaped_advances(micro_light_cmap_ttf_path, "IO")
    assert len(advances) == 2
    assert advances[0][1] == 600
    assert advances[1][1] == 600


def test_shaped_positions_carries_offsets(micro_light_cmap_ttf_path):
    # Same run as shaped_advances but with the GPOS placement offsets retained.
    positions = qa_deep.shaped_positions(micro_light_cmap_ttf_path, "IO")
    assert len(positions) == 2
    for name, advance, x_off, y_off in positions:
        assert advance == 600
        assert x_off == 0 and y_off == 0
        assert isinstance(name, str)


def test_collision_free_io(micro_light_cmap_ttf_path):
    assert qa_deep.collision_free(micro_light_cmap_ttf_path, "IO") is True


def test_collision_free_detects_overlap(micro_light_cmap_ttf_path, tmp_path):
    """Widen ink past the advance so adjacent 'I' cells collide."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    path = tmp_path / "wide.ttf"
    shutil.copy(micro_light_cmap_ttf_path, path)
    font = TTFont(path)
    pen = TTGlyphPen(None)
    # Full-cell rectangle: left -50 → right 650 on a 600 advance → neighbour overlap.
    pen.moveTo((-50, 0))
    pen.lineTo((650, 0))
    pen.lineTo((650, 700))
    pen.lineTo((-50, 700))
    pen.closePath()
    font["glyf"]["I"] = pen.glyph()
    font.save(path)
    assert qa_deep.collision_free(path, "II") is False


def test_stem_profile_uses_l_at_400(micro_light_ttf):
    # Micro "l" is a copy of "I": stem x 280-320 -> width 40 at y=400.
    assert qa_deep.stem_profile(micro_light_ttf) == pytest.approx(40, abs=1)


def test_stem_profile_bold_heavier(micro_light_ttf, micro_bold_ttf):
    assert qa_deep.stem_profile(micro_bold_ttf) > qa_deep.stem_profile(micro_light_ttf)


def test_outline_max_delta_skips_missing_glyph(micro_light_ttf):
    # Glyph name absent from both fonts is skipped (delta stays 0).
    assert qa_deep.outline_max_delta(micro_light_ttf, micro_light_ttf, ["nope"]) == 0.0


def test_strip_hinting_without_glyf(micro_light_ttf):
    font = micro_light_ttf
    del font["glyf"]
    qa_deep.strip_hinting(font)  # must not raise


def test_collision_free_skips_construction_glyphs(micro_light_cmap_ttf_path, tmp_path):
    """A wide ``.liga`` glyph that spans cells must not be flagged as a collision."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    path = tmp_path / "liga.ttf"
    shutil.copy(micro_light_cmap_ttf_path, path)
    font = TTFont(path)
    pen = TTGlyphPen(None)
    pen.moveTo((-50, 0))
    pen.lineTo((1250, 0))
    pen.lineTo((1250, 700))
    pen.lineTo((-50, 700))
    pen.closePath()
    # Overwrite "I" outline to be wide, but shape under a construction name by
    # adding I.liga and remapping cmap + glyph order entry used for U+0049.
    glyf = font["glyf"]
    metrics = font["hmtx"].metrics["I"]
    glyf["I.liga"] = pen.glyph()
    font["hmtx"].metrics["I.liga"] = metrics
    for table in font["cmap"].tables:
        if table.isUnicode() and 0x49 in table.cmap:
            table.cmap[0x49] = "I.liga"
    font.save(path)
    # Two wide construction glyphs would overlap if not skipped.
    assert qa_deep.collision_free(path, "II") is True


def test_ink_bounds_none_for_empty_glyph(micro_light_ttf):
    # space-like empty path → _ink_bounds returns None (no collision contribution).
    assert qa_deep._ink_bounds(micro_light_ttf, ".notdef") is not None  # has ink
    # Clear .notdef to empty.
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    pen = TTGlyphPen(None)
    micro_light_ttf["glyf"][".notdef"] = pen.glyph()
    assert qa_deep._ink_bounds(micro_light_ttf, ".notdef") is None
