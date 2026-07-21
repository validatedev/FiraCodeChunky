"""Integration checks for FiraCodeChunky Nerd Font Mono statics in dist/nerd/.

Skipped when inputs are absent (mirror tests/integration skip-when-upstream-missing):
  - dist/ttf sources missing → skip
  - dist/nerd outputs missing → skip
  - fontforge / patcher not required at test time (only the produced TTFs)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
DIST_TTF = ROOT / "dist" / "ttf"
DIST_NERD = ROOT / "dist" / "nerd"

STYLES_WEIGHTS = (
    ("Light", 300),
    ("Regular", 400),
    ("Medium", 500),
    ("SemiBold", 600),
    ("Bold", 700),
)

# Stable codepoints from nerd-fonts v3.4.0 complete set (verified against
# FontPatcher.zip glyphnames / patched cmap):
#   U+E0A0  Powerline branch symbol
#   U+F015  Font Awesome house
#   U+F448  Octicons pencil
NERD_CODEPOINTS = (0xE0A0, 0xF015, 0xF448)


def _nerd_path(style: str) -> Path:
    return DIST_NERD / f"FiraCodeChunkyNerdFontMono-{style}.ttf"


def _src_path(style: str) -> Path:
    return DIST_TTF / f"FiraCodeChunky-{style}.ttf"


requires_sources = pytest.mark.skipif(
    not all(_src_path(s).exists() for s, _ in STYLES_WEIGHTS),
    reason="run `uv run chunky-build` first (dist/ttf missing)",
)

requires_nerd = pytest.mark.skipif(
    not all(_nerd_path(s).exists() for s, _ in STYLES_WEIGHTS),
    reason="run `uv run python scripts/build_nerd.py` first (dist/nerd missing)",
)


def _family_name(font: TTFont) -> str:
    """Best-effort English family name (nameID 1, else 16)."""
    name = font["name"]
    for nid in (1, 16):
        for rec in name.names:
            if rec.nameID != nid:
                continue
            try:
                return rec.toUnicode()
            except UnicodeDecodeError:
                continue
    return ""


def _best_cmap(font: TTFont) -> dict[int, str]:
    cmap = font.getBestCmap()
    assert cmap is not None
    return cmap


def _glyph_outline(font: TTFont, glyph_name: str) -> list:
    glyf = font["glyf"]
    pen = RecordingPen()
    glyf[glyph_name].draw(pen, glyf)
    return pen.value


@requires_sources
@requires_nerd
@pytest.mark.parametrize(("style", "weight"), STYLES_WEIGHTS)
def test_nerd_family_contains_nerd_font(style: str, weight: int) -> None:
    font = TTFont(_nerd_path(style))
    family = _family_name(font)
    assert "Nerd Font" in family, f"{style}: family={family!r}"


@requires_sources
@requires_nerd
@pytest.mark.parametrize(("style", "weight"), STYLES_WEIGHTS)
def test_nerd_weight_matches_source(style: str, weight: int) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style))
    src_wc = cast(Any, src["OS/2"]).usWeightClass
    nerd_wc = cast(Any, nerd["OS/2"]).usWeightClass
    assert src_wc == weight
    assert nerd_wc == weight
    assert nerd_wc == src_wc


@requires_sources
@requires_nerd
@pytest.mark.parametrize(("style", "weight"), STYLES_WEIGHTS)
def test_nerd_iconic_codepoints_present(style: str, weight: int) -> None:
    font = TTFont(_nerd_path(style))
    cmap = _best_cmap(font)
    missing = [f"U+{cp:04X}" for cp in NERD_CODEPOINTS if cp not in cmap]
    assert not missing, f"{style}: missing Nerd Font codepoints {missing}"


@requires_sources
@requires_nerd
@pytest.mark.parametrize(("style", "weight"), STYLES_WEIGHTS)
def test_nerd_base_glyph_H_outline_identical(style: str, weight: int) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style))
    src_cmap = _best_cmap(src)
    nerd_cmap = _best_cmap(nerd)
    assert ord("H") in src_cmap and ord("H") in nerd_cmap
    src_g = src_cmap[ord("H")]
    nerd_g = nerd_cmap[ord("H")]
    assert _glyph_outline(src, src_g) == _glyph_outline(nerd, nerd_g)


@requires_sources
@requires_nerd
@pytest.mark.parametrize(("style", "weight"), STYLES_WEIGHTS)
def test_nerd_monospace_preserved(style: str, weight: int) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style))
    src_cmap = _best_cmap(src)
    nerd_cmap = _best_cmap(nerd)
    src_h = src_cmap[ord("H")]
    nerd_h = nerd_cmap[ord("H")]
    assert src["hmtx"][src_h][0] == nerd["hmtx"][nerd_h][0]
    assert cast(Any, nerd["post"]).isFixedPitch == 1
    assert cast(Any, src["post"]).isFixedPitch == 1
