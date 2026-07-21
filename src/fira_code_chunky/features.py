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

if TYPE_CHECKING:
    import ufoLib2

_CV_BLOCK = re.compile(r"feature\s+(cv\d\d)\s*\{.*?\}\s*\1\s*;", re.DOTALL)
_FEATURE_NAMES = re.compile(r"featureNames\s*\{(.*?)\}\s*;", re.DOTALL)


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
    if categories:
        font.lib["public.openTypeCategories"] = categories
    return categories
