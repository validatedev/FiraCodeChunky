"""Prepare UFO OpenType feature state for feaLib / ufo2ft compilation.

Two jobs:

1. **cvXX featureNames.** Fira Code's Glyphs source labels character-variant
   features (cv01, cv02, ...) with ``featureNames`` blocks. glyphs2ufo writes
   those verbatim into each UFO's ``features.fea``. feaLib only accepts
   ``featureNames`` inside stylistic-set features (ss01-ss20); a character-
   variant feature must use ``cvParameters { FeatUILabelNameID { ... } }``.
   :func:`sanitize_features` rewrites only the offending cvXX blocks and leaves
   ssXX ``featureNames`` (and everything else) untouched.

2. **GDEF categories for spacing diacritics.** Spacing accents such as U+0060
   GRAVE ACCENT (glyph ``grave``) carry a ``_top`` mark anchor so they can be
   used as components in accented letters. Without an explicit
   ``public.openTypeCategories`` map, ufo2ft's mark feature writer treats every
   glyph that has a ``_``-prefixed anchor as a mark class member; feaLib then
   puts those glyphs in GDEF as marks. HarfBuzz zeros the advance of GDEF
   marks and mark-positions them onto the previous base, so terminal runs like
   ``S` `` render as a combining grave on S instead of a standalone backtick.
   Official Fira Code leaves spacing diacritics out of GDEF mark class.
   :func:`ensure_opentype_categories` writes the same categories glyphsLib
   would emit with ``--generate-GDEF``: true combining marks only, not spacing
   accents.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fira_code_chunky.qa import QAError

if TYPE_CHECKING:
    import ufoLib2

_CV_BLOCK = re.compile(r"feature\s+(cv\d\d)\s*\{.*?\}\s*\1\s*;", re.DOTALL)
_FEATURE_NAMES = re.compile(r"featureNames\s*\{(.*?)\}\s*;", re.DOTALL)

# Glyphs stores a zeroed advance + this lib key for combining marks; the value
# is the intended spacing width (1200 in Fira Code).
_ORIGINAL_WIDTH_KEY = "com.schriftgestaltung.Glyphs.originalWidth"

# Glyphs that upstream Fira Code 6.002 ships as SPACING (advance 1200, GDEF
# unclassified, absent from GPOS mark coverage) even though glyphsLib classifies
# them as marks and the Glyphs->UFO conversion zeroes their advance. Verified
# against the official FiraCode-Regular.ttf binary: strokeshortoverlay (U+0335),
# strokelongoverlay (U+0336) and commaaccent.case (production name uni0326.case,
# reached via ccmp after capitals). True combining marks (gravecomb, commaaccent
# non-.case, dotaccentcomb, ...) are deliberately EXCLUDED and keep advance 0 /
# GDEF mark class, matching upstream (F1/F2).
_SPACING_OVERRIDES = ("strokeshortoverlay", "strokelongoverlay", "commaaccent.case")


def _wrap_names(match: re.Match[str]) -> str:
    return f"cvParameters {{\nFeatUILabelNameID {{{match.group(1)}}};\n}};"


def _fix_cv_block(match: re.Match[str]) -> str:
    return _FEATURE_NAMES.sub(_wrap_names, match.group(0))


def sanitize_features(text: str) -> str:
    """Convert cvXX ``featureNames`` blocks into valid ``cvParameters``."""
    return _CV_BLOCK.sub(_fix_cv_block, text)


def ensure_opentype_categories(font: ufoLib2.Font) -> dict[str, str]:
    """Write ``public.openTypeCategories`` so spacing diacritics stay non-marks.

    Uses glyphsLib's GlyphData-based classifier (Mark + Nonspacing / Spacing
    Combining → mark; attaching-anchor glyphs → base; ligatures → ligature).
    Spacing diacritics such as ``grave`` (Mark/Spacing) are left unassigned so
    ufo2ft does not put them in a mark class.
    """
    # Same classifier glyphs2ufo --generate-GDEF uses; kept private there but
    # is the one authoritative mapping for Glyphs-sourced UFOs.
    from glyphsLib.builder.features import _build_public_opentype_categories

    categories = _build_public_opentype_categories(font)
    _restore_spacing_overrides(font, categories)
    if categories:
        font.lib["public.openTypeCategories"] = categories
    else:
        # A stale map left in lib would still reach ufo2ft; drop it.
        font.lib.pop("public.openTypeCategories", None)
    return categories


def _restore_spacing_overrides(font: ufoLib2.Font, categories: dict[str, str]) -> None:
    """Un-mark the spacing overlays and restore their 1200 advance (F1/F2).

    Mutates ``categories`` in place: drops the override glyphs so ufo2ft leaves
    them GDEF-unclassified, and resets each glyph's advance from its stored
    ``originalWidth`` so HarfBuzz stops collapsing them onto the previous base.
    """
    for name in _SPACING_OVERRIDES:
        if name not in font:
            continue
        original = font[name].lib.get(_ORIGINAL_WIDTH_KEY)
        # Never emit an un-marked, zero-advance override: without a positive
        # originalWidth we cannot restore the spacing cell, so fail the build
        # loudly rather than shipping a collapsed glyph.
        if not original or original <= 0:
            raise QAError(
                f"spacing override {name!r} has no positive originalWidth "
                f"(got {original!r}); cannot restore its 1200 advance"
            )
        font[name].width = original
        categories.pop(name, None)
