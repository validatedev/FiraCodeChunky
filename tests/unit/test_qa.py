import pytest

from fira_code_chunky import metadata, qa


def pin_valid_metadata(font, style="Regular", weight_class=400):
    metadata.pin_all(font, "Fira Code Chunky", style, weight_class)


def test_normalized_ttx_scrubs_volatile(micro_ttf):
    out = qa.normalized_ttx(micro_ttf, tables=("head",))
    assert "checkSumAdjustment" not in out
    assert "modified" not in out


def test_normalized_ttx_stable_across_saves(micro_ttf, tmp_path):
    from fontTools.ttLib import TTFont

    a = qa.normalized_ttx(micro_ttf)
    p = tmp_path / "again.ttf"
    micro_ttf.save(p)
    assert qa.normalized_ttx(TTFont(p)) == a


def test_assert_static_metadata_passes_after_pin(micro_ttf):
    pin_valid_metadata(micro_ttf)
    qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_450_regular(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].usWeightClass = 450  # the classic silent defect
    with pytest.raises(qa.QAError, match="usWeightClass"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_stem_width_micro_light(micro_ttf):
    # MicroLight "I": stem x 280-320 -> width 40 at mid-height
    assert qa.stem_width(micro_ttf, "I", 350) == pytest.approx(40, abs=1)


def test_glyph_overlap_detection(micro_ttf):
    assert not qa.glyph_has_overlap(micro_ttf, "I")


def test_assert_static_metadata_passes_non_ribbi(micro_ttf):
    # Non-RIBBI style exercises name 16/17 and the typographic-family branch.
    pin_valid_metadata(micro_ttf, "Medium", 500)
    qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Medium", 500)


def test_assert_static_metadata_passes_bold(micro_ttf):
    # Bold exercises the want_bold=True side of every bit check.
    pin_valid_metadata(micro_ttf, "Bold", 700)
    qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Bold", 700)


def test_assert_static_metadata_catches_wrong_name(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].setName("Wrong Family", 1, *metadata.WIN)
    with pytest.raises(qa.QAError, match="name 1"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_wrong_postscript_name(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].setName("WrongPSName", 6, *metadata.WIN)
    with pytest.raises(qa.QAError, match="name 6"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_non_fixed_pitch(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["post"].isFixedPitch = 0
    with pytest.raises(qa.QAError, match="isFixedPitch"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_wrong_width_class(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].usWidthClass = 4
    with pytest.raises(qa.QAError, match="usWidthClass"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_ribbi_typographic_names(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].setName("Fira Code Chunky", 16, *metadata.WIN)
    with pytest.raises(qa.QAError, match="must not carry name 16/17"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_bold_bit(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].fsSelection |= metadata.FS_BOLD
    with pytest.raises(qa.QAError, match="fsSelection BOLD bit wrong"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_regular_bit(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].fsSelection &= ~metadata.FS_REGULAR
    with pytest.raises(qa.QAError, match="fsSelection REGULAR bit wrong"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_macstyle(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["head"].macStyle |= metadata.MAC_BOLD
    with pytest.raises(qa.QAError, match="macStyle bold bit wrong"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_missing_copyright(micro_ttf):
    # Fix 1 regression gate: name ID 0 (copyright) is exactly what the
    # extrapolated Bold used to ship without.
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].removeNames(nameID=0)
    with pytest.raises(qa.QAError, match="name 0"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_missing_license(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].removeNames(nameID=13)
    with pytest.raises(qa.QAError, match="name 13"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_missing_license_url(micro_ttf):
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].removeNames(nameID=14)
    with pytest.raises(qa.QAError, match="name 14"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_empty_copyright(micro_ttf):
    # Blank-but-present records must also fail, not just absent ones.
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].setName("", 0, *metadata.WIN)
    with pytest.raises(qa.QAError, match="name 0"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_restricted_fstype(micro_ttf):
    # F5: fsType=4 (Restricted License embedding) is exactly what the Bold shipped.
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].fsType = 4
    with pytest.raises(qa.QAError, match="fsType"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_missing_use_typo_metrics(micro_ttf):
    # F7: the Bold dropped fsSelection bit 7 (USE_TYPO_METRICS).
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].fsSelection &= ~metadata.FS_USE_TYPO_METRICS
    with pytest.raises(qa.QAError, match="USE_TYPO_METRICS"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_extrapolated_underline(micro_ttf):
    # F4: the Bold extrapolated underline to -146/98 instead of the family -100/50.
    pin_valid_metadata(micro_ttf)
    micro_ttf["post"].underlinePosition = -146
    with pytest.raises(qa.QAError, match="underline"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_extrapolated_strikeout(micro_ttf):
    # F4: the Bold extrapolated strikeout to 638/98 instead of 318/50.
    pin_valid_metadata(micro_ttf)
    micro_ttf["OS/2"].yStrikeoutSize = 98
    with pytest.raises(qa.QAError, match="strikeout"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_missing_designer_name(micro_ttf):
    # F7: name IDs 8/9/11/12 (manufacturer/designer + URLs) were missing on Bold.
    pin_valid_metadata(micro_ttf)
    micro_ttf["name"].removeNames(nameID=9)
    with pytest.raises(qa.QAError, match="name 9"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_skip_export_leak(micro_ttf):
    # F6: a leaked _part.* build glyph must be caught.
    pin_valid_metadata(micro_ttf)
    micro_ttf.setGlyphOrder([*micro_ttf.getGlyphOrder(), "_part.numbersign"])
    with pytest.raises(qa.QAError, match="skip-export leak"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_assert_static_metadata_catches_broken_advance_width_max(micro_ttf):
    # F6: the leaked build part pushed advanceWidthMax to 2562, above the cell.
    pin_valid_metadata(micro_ttf)
    micro_ttf["hhea"].advanceWidthMax = 2562
    with pytest.raises(qa.QAError, match="advanceWidthMax"):
        qa.assert_static_metadata(micro_ttf, "Fira Code Chunky", "Regular", 400)


def test_stem_width_raises_without_ink(micro_ttf):
    # y=5000 is far above the "I" glyph, so the band intersects no ink.
    with pytest.raises(qa.QAError, match="no ink"):
        qa.stem_width(micro_ttf, "I", 5000)


def test_glyph_overlap_detects_self_intersection(micro_ttf):
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    # fontmake strips overlaps at compile time, so inject a self-overlapping
    # outline directly into the glyf table to exercise the True branch.
    pen = TTGlyphPen(None)
    for x0 in (0, 50):
        pen.moveTo((x0, 0))
        pen.lineTo((x0 + 100, 0))
        pen.lineTo((x0 + 100, 100))
        pen.lineTo((x0, 100))
        pen.closePath()
    micro_ttf["glyf"]["I"] = pen.glyph()
    assert qa.glyph_has_overlap(micro_ttf, "I")


def test_has_calt(micro_ttf):
    assert qa.has_calt(micro_ttf)


def test_has_calt_false_without_gsub(micro_ttf):
    if "GSUB" in micro_ttf:
        del micro_ttf["GSUB"]
    assert not qa.has_calt(micro_ttf)
