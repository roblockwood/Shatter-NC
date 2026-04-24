"""Tests for Brother FTP sync exclusion and naming rules."""

from app.utils.ftp_sync_rules import validate_brother_filename


def test_allows_valid_onumber_filename():
    decision = validate_brother_filename(
        "O2000.NC",
        control_type="C00",
        strict_naming=True,
        require_onumber=True,
        exclude_patterns=[],
    )
    assert decision.allowed is True


def test_rejects_non_nc_extension():
    decision = validate_brother_filename(
        "O2000.TXT",
        control_type="C00",
        strict_naming=True,
        require_onumber=True,
        exclude_patterns=[],
    )
    assert decision.allowed is False
    assert decision.reason == "unsupported_extension"


def test_rejects_lowercase_filename():
    decision = validate_brother_filename(
        "o2000.NC",
        control_type="C00",
        strict_naming=True,
        require_onumber=True,
        exclude_patterns=[],
    )
    assert decision.allowed is False
    assert decision.reason == "filename_must_be_uppercase"


def test_rejects_reserved_system_filename():
    decision = validate_brother_filename(
        "ALARM.NC",
        control_type="C00",
        strict_naming=True,
        require_onumber=False,
        exclude_patterns=[],
    )
    assert decision.allowed is False
    assert decision.reason == "reserved_system_filename"


def test_rejects_non_onumber_when_required():
    decision = validate_brother_filename(
        "PART1.NC",
        control_type="C00",
        strict_naming=True,
        require_onumber=True,
        exclude_patterns=[],
    )
    assert decision.allowed is False
    assert decision.reason == "requires_onumber_filename"


def test_rejects_long_name_for_c00():
    decision = validate_brother_filename(
        "TOO_LONG_01.NC",
        control_type="C00",
        strict_naming=True,
        require_onumber=False,
        exclude_patterns=[],
    )
    assert decision.allowed is False
    assert decision.reason == "filename_too_long_for_C00"


def test_allows_longer_name_for_d00():
    decision = validate_brother_filename(
        "PROGRAM_FILE_1234567890.NC",
        control_type="D00",
        strict_naming=True,
        require_onumber=False,
        exclude_patterns=[],
    )
    assert decision.allowed is True


def test_applies_exclude_patterns():
    decision = validate_brother_filename(
        "PART001.tmp",
        control_type="D00",
        strict_naming=True,
        require_onumber=False,
        exclude_patterns=["*.tmp"],
    )
    assert decision.allowed is False
    assert decision.reason == "filename_matches_exclude_pattern"
