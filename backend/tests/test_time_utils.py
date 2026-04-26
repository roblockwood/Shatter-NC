"""Tests for the CNC time string formatting utility."""
import pytest
from app.utils.time_utils import format_cnc_time


def test_formats_normal_time():
    """Standard 9-char HHMMSSMMM → HHMM:SS.MMM."""
    assert format_cnc_time("123456789") == "1234:56.789"


def test_formats_zero_time():
    """All-zero time string produces zero display."""
    assert format_cnc_time("000000000") == "0000:00.000"


def test_formats_midnight():
    """Midnight boundary: 00h 00m 00s 000ms."""
    assert format_cnc_time("000000000") == "0000:00.000"


def test_formats_max_time():
    """Large hour value is preserved as-is without overflow."""
    assert format_cnc_time("235959999") == "2359:59.999"


def test_returns_original_when_too_short():
    """Strings shorter than 9 chars pass through unchanged."""
    short = "12345"
    assert format_cnc_time(short) == short


def test_returns_original_when_too_long():
    """Strings longer than 9 chars pass through unchanged."""
    long_str = "1234567890"
    assert format_cnc_time(long_str) == long_str


def test_returns_original_when_empty_string():
    """Empty string passes through unchanged."""
    assert format_cnc_time("") == ""


def test_returns_original_when_none():
    """None passes through unchanged."""
    assert format_cnc_time(None) is None


def test_field_positions_are_correct():
    """Assert each sub-field maps to the right position."""
    result = format_cnc_time("010203456")
    hhmm, rest = result.split(":")
    ss, mmm = rest.split(".")
    assert hhmm == "0102"
    assert ss == "03"
    assert mmm == "456"
