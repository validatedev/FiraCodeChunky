"""Integration checks for the three FiraCodeChunky Nerd Font variants in dist/nerd/.

Skipped when inputs are absent (mirror tests/integration skip-when-upstream-missing):
  - dist/ttf sources missing → skip
  - dist/nerd outputs missing (per variant/style, or all of them) → skip
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

# (id, family, stem_infix, expected_fixed_pitch). Mirrors scripts/build_nerd.py
# VARIANTS. stem_infix "" (plain) is intentionally empty; never branch on its
# truthiness — that would silently drop the plain variant from the test matrix.
#
# plain's expected_fixed_pitch is 1, not 0: our source is a clean monospace,
# so plain's advances are all one cell (Nerd icons overhang in the OUTLINE
# only, not the advance width), and FontForge computes isFixedPitch=1 from
# that. Upstream stock Fira Code's plain was 0 only because of one 650-unit
# oddball glyph our font doesn't have. Here plain and Mono both report
# isFixedPitch=1; they're distinguished by family/PostScript name and by the
# icon outline-overhang test (see test_nerd_plain_icons_overhang_more_than_mono),
# not by isFixedPitch.
VARIANTS = (
    ("plain", "FiraCodeChunky Nerd Font", "", 1),
    ("mono", "FiraCodeChunky Nerd Font Mono", "Mono", 1),
    ("propo", "FiraCodeChunky Nerd Font Propo", "Propo", 0),
)

# Stable codepoints from nerd-fonts v3.4.0 complete set (verified against
# FontPatcher.zip glyphnames / patched cmap):
#   U+E0A0  Powerline branch symbol
#   U+F015  Font Awesome house
#   U+F448  Octicons pencil
NERD_CODEPOINTS = (0xE0A0, 0xF015, 0xF448)


def _nerd_path(style: str, stem_infix: str) -> Path:
    return DIST_NERD / f"FiraCodeChunkyNerdFont{stem_infix}-{style}.ttf"


def _src_path(style: str) -> Path:
    return DIST_TTF / f"FiraCodeChunky-{style}.ttf"


def _all_expected_paths() -> list[Path]:
    return [
        _nerd_path(style, stem_infix)
        for _vid, _family, stem_infix, _expected_fixed_pitch in VARIANTS
        for style, _weight in STYLES_WEIGHTS
    ]


requires_sources = pytest.mark.skipif(
    not all(_src_path(s).exists() for s, _ in STYLES_WEIGHTS),
    reason="run `uv run chunky-build` first (dist/ttf missing)",
)

# Whole-module skip only when dist/nerd has zero .ttf files at all — keyed on
# actual directory contents, not on the _nerd_path()/stem_infix naming formula.
# If that formula ever typos while the 15 real files exist, checking against
# _all_expected_paths() would silently skip the whole suite instead of
# running test_nerd_all_variants_complete_with_unique_postscript_names and
# failing loudly on the mismatch.
if not any(DIST_NERD.glob("*.ttf")):
    pytest.skip(
        "run `uv run python scripts/build_nerd.py` first (dist/nerd empty)",
        allow_module_level=True,
    )


def _requires_variant(stem_infix: str, style: str) -> pytest.MarkDecorator:
    path = _nerd_path(style, stem_infix)
    return pytest.mark.skipif(
        not path.exists(),
        reason=f"{path.name} not built",
    )


def _variant_style_params():
    params = []
    for vid, family, stem_infix, expected_fixed_pitch in VARIANTS:
        for style, weight in STYLES_WEIGHTS:
            params.append(
                pytest.param(
                    vid,
                    family,
                    stem_infix,
                    expected_fixed_pitch,
                    style,
                    weight,
                    id=f"{vid}-{style}",
                    marks=_requires_variant(stem_infix, style),
                )
            )
    return params


VARIANT_STYLE_PARAMS = _variant_style_params()


def _family_name(font: TTFont) -> str:
    """Exact typographic family name.

    Prefer nameID 16 (typographic family): this legacy-RIBBI source only sets
    it for weights that don't fit the 4-way Regular/Bold/Italic/BoldItalic
    model (Light/Medium/SemiBold), where nameID 1 instead gets the style
    suffixed onto it (e.g. "... Nerd Font Mono Medium") to keep old apps
    happy. For Regular/Bold, nameID 16 is absent and nameID 1 already equals
    the plain family, so falling back to nameID 1 there is correct too.
    """
    name = font["name"]
    for nid in (16, 1):
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
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_family_name_exact(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    font = TTFont(_nerd_path(style, stem_infix))
    actual = _family_name(font)
    assert actual == family, f"{vid}-{style}: family={actual!r}, expected {family!r}"


@requires_sources
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_weight_matches_source(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style, stem_infix))
    src_wc = cast(Any, src["OS/2"]).usWeightClass
    nerd_wc = cast(Any, nerd["OS/2"]).usWeightClass
    assert src_wc == weight
    assert nerd_wc == weight
    assert nerd_wc == src_wc


@requires_sources
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_iconic_codepoints_present(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    font = TTFont(_nerd_path(style, stem_infix))
    cmap = _best_cmap(font)
    missing = [f"U+{cp:04X}" for cp in NERD_CODEPOINTS if cp not in cmap]
    assert not missing, f"{vid}-{style}: missing Nerd Font codepoints {missing}"


@requires_sources
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_base_glyph_H_outline_identical(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style, stem_infix))
    src_cmap = _best_cmap(src)
    nerd_cmap = _best_cmap(nerd)
    assert ord("H") in src_cmap and ord("H") in nerd_cmap
    src_g = src_cmap[ord("H")]
    nerd_g = nerd_cmap[ord("H")]
    assert _glyph_outline(src, src_g) == _glyph_outline(nerd, nerd_g)


@requires_sources
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_H_advance_matches_source(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style, stem_infix))
    src_cmap = _best_cmap(src)
    nerd_cmap = _best_cmap(nerd)
    src_h = src_cmap[ord("H")]
    nerd_h = nerd_cmap[ord("H")]
    assert src["hmtx"][src_h][0] == nerd["hmtx"][nerd_h][0]


@requires_sources
@pytest.mark.parametrize(
    ("vid", "family", "stem_infix", "expected_fixed_pitch", "style", "weight"),
    VARIANT_STYLE_PARAMS,
)
def test_nerd_fixed_pitch_matches_variant(
    vid: str,
    family: str,
    stem_infix: str,
    expected_fixed_pitch: int,
    style: str,
    weight: int,
) -> None:
    nerd = TTFont(_nerd_path(style, stem_infix))
    actual = cast(Any, nerd["post"]).isFixedPitch
    assert actual == expected_fixed_pitch, (
        f"{vid}-{style}: isFixedPitch={actual}, expected {expected_fixed_pitch}"
    )


_PROPO_STYLE_PARAMS = [
    pytest.param(style, marks=_requires_variant("Propo", style))
    for style, _weight in STYLES_WEIGHTS
]


@requires_sources
@pytest.mark.parametrize("style", _PROPO_STYLE_PARAMS)
def test_nerd_propo_has_variable_icon_advances(style: str) -> None:
    src = TTFont(_src_path(style))
    nerd = TTFont(_nerd_path(style, "Propo"))
    src_cmap = _best_cmap(src)
    h_advance = src["hmtx"][src_cmap[ord("H")]][0]
    nerd_cmap = _best_cmap(nerd)
    icon_advances = []
    for cp in NERD_CODEPOINTS:
        assert cp in nerd_cmap
        icon_advances.append(nerd["hmtx"][nerd_cmap[cp]][0])
    assert any(adv != h_advance for adv in icon_advances), (
        f"propo-{style}: expected at least one sample icon advance != H advance "
        f"({h_advance}), got {icon_advances}"
    )


def _count_overhanging_glyphs(font: TTFont) -> int:
    """Count glyphs whose glyf outline bbox width exceeds their advance width.

    An "overhanging" glyph is one whose drawn outline is wider than the cell
    it advances by — e.g. a Nerd Font icon squeezed into a monospace cell
    but drawn wider than that cell, so it visually spills into neighboring
    glyphs. plain (no per-icon advance rescaling) has far more of these than
    Mono (which scales icons to fit one cell).
    """
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    count = 0
    for name in glyf.keys():  # noqa: SIM118 - glyf is a fontTools table, not a dict
        glyph = glyf[name]
        if glyph.numberOfContours == 0:
            continue
        glyph.recalcBounds(glyf)
        width = glyph.xMax - glyph.xMin
        advance = hmtx[name][0]
        if width > advance:
            count += 1
    return count


_OVERHANG_STYLE_PARAMS = [
    pytest.param(
        style,
        marks=[_requires_variant("", style), _requires_variant("Mono", style)],
    )
    for style, _weight in STYLES_WEIGHTS
]


@requires_sources
@pytest.mark.parametrize("style", _OVERHANG_STYLE_PARAMS)
def test_nerd_plain_icons_overhang_more_than_mono(style: str) -> None:
    plain = TTFont(_nerd_path(style, ""))
    mono = TTFont(_nerd_path(style, "Mono"))
    plain_count = _count_overhanging_glyphs(plain)
    mono_count = _count_overhanging_glyphs(mono)
    assert plain_count > mono_count, (
        f"plain_count={plain_count}, mono_count={mono_count}: expected plain to "
        f"have more outline-overhanging glyphs than Mono at {style}"
    )
    # The >1000 margin tracks the pinned nerd-fonts v3.4.0 glyph population;
    # re-verify this threshold if the patcher's glyph set version changes.
    assert (plain_count - mono_count) > 1000, (
        f"plain_count={plain_count}, mono_count={mono_count}: margin "
        f"{plain_count - mono_count} too small (<=1000) to reliably distinguish "
        f"plain from Mono at the glyph level ({style})"
    )


# PostScript-name abbrev (the segment before the first "-", with the family
# prefix stripped) expected per variant: plain -> NF, mono -> NFM, propo ->
# NFP. Keyed off stem_infix so a --mono leak into the plain build (which
# would still produce a file at the plain path but named FiraCodeChunkyNFM-*)
# is caught, not just cross-variant duplicate collisions.
_EXPECTED_ABBREV_BY_STEM_INFIX = {"": "NF", "Mono": "NFM", "Propo": "NFP"}


@requires_sources
def test_nerd_all_variants_complete_with_unique_postscript_names() -> None:
    expected = _all_expected_paths()
    missing = [p for p in expected if not p.exists()]
    assert not missing, f"missing nerd outputs: {[p.name for p in missing]}"

    stem_infix_by_path = {
        _nerd_path(style, stem_infix): stem_infix
        for _vid, _family, stem_infix, _expected_fixed_pitch in VARIANTS
        for style, _weight in STYLES_WEIGHTS
    }

    ps_names: dict[str, list[str]] = {}
    for path in expected:
        font = TTFont(path)
        name = font["name"]
        ps_name = ""
        for rec in name.names:
            if rec.nameID != 6:
                continue
            try:
                ps_name = rec.toUnicode()
                break
            except UnicodeDecodeError:
                continue
        assert ps_name, f"{path.name}: empty/missing PostScript name (nameID 6)"
        ps_names.setdefault(ps_name, []).append(path.name)

        stem_infix = stem_infix_by_path[path]
        expected_abbrev = _EXPECTED_ABBREV_BY_STEM_INFIX[stem_infix]
        abbrev = ps_name.split("-")[0].removeprefix("FiraCodeChunky")
        assert abbrev == expected_abbrev, (
            f"{path.name}: PostScript name {ps_name!r} has abbrev {abbrev!r}, "
            f"expected {expected_abbrev!r}"
        )

    duplicates = {name: files for name, files in ps_names.items() if len(files) > 1}
    assert not duplicates, f"duplicate PostScript names (nameID 6): {duplicates}"
