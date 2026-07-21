"""Sanitize glyphsLib-generated feature code for feaLib compilation.

Fira Code's Glyphs source labels its character-variant features (cv01, cv02,
...) with ``featureNames`` blocks. glyphs2ufo writes those verbatim into each
UFO's ``features.fea``. feaLib, however, only accepts ``featureNames`` inside
stylistic-set features (ss01-ss20); a character-variant feature must express
its UI label through ``cvParameters { FeatUILabelNameID { ... } }``. Compiling
the raw UFO therefore fails with "Expected glyph class definition or statement:
got NAME featureNames".

:func:`sanitize_features` rewrites only the offending cvXX blocks and leaves
ssXX ``featureNames`` (and everything else) untouched.
"""

from __future__ import annotations

import re

_CV_BLOCK = re.compile(r"feature\s+(cv\d\d)\s*\{.*?\}\s*\1\s*;", re.DOTALL)
_FEATURE_NAMES = re.compile(r"featureNames\s*\{(.*?)\}\s*;", re.DOTALL)


def _wrap_names(match: re.Match[str]) -> str:
    return f"cvParameters {{\nFeatUILabelNameID {{{match.group(1)}}};\n}};"


def _fix_cv_block(match: re.Match[str]) -> str:
    return _FEATURE_NAMES.sub(_wrap_names, match.group(0))


def sanitize_features(text: str) -> str:
    """Convert cvXX ``featureNames`` blocks into valid ``cvParameters``."""
    return _CV_BLOCK.sub(_fix_cv_block, text)
