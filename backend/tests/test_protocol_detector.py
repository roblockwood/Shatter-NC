"""Tests for protocol detector with mocked sockets / clients."""
from unittest.mock import MagicMock, patch

import pytest

from app.utils.protocol_detector import ProtocolDetector, detect_protocols


def test_scan_ports_closed():
    detector = ProtocolDetector("10.0.0.1", timeout=0.1)
    with patch.object(detector, "_check_port", return_value=(False, None)):
        results = detector.scan_ports([9999])
    assert results == [{"port": 9999, "open": False, "banner": None}]


def test_scan_ports_open_with_banner():
    detector = ProtocolDetector("10.0.0.1")
    with patch.object(detector, "_check_port", return_value=(True, "FOCAS hello")):
        results = detector.scan_ports([8193])
    assert results[0]["open"] is True
    assert results[0]["banner"] == "FOCAS hello"


def test_check_focas_port_likely():
    detector = ProtocolDetector("10.0.0.1")
    with patch.object(detector, "_check_port", return_value=(True, "banner")):
        result = detector._check_focas_port(8193)
    assert result["open"] is True
    assert result["likely_focas"] is True
    assert "FOCAS" in result["protocol"]


def test_detect_all_summary():
    detector = ProtocolDetector("10.0.0.1")

    def fake_focas(port):
        return {
            "port": port,
            "open": port == 8193,
            "likely_focas": port == 8193,
            "protocol": "FOCAS1/Ethernet (likely)" if port == 8193 else None,
            "banner": "x" if port == 8193 else None,
        }

    with patch.object(detector, "_check_focas_port", side_effect=fake_focas):
        with patch.object(
            detector,
            "scan_ports",
            return_value=[{"port": 23, "open": True, "banner": "Telnet"}],
        ):
            result = detector.detect_all()

    assert result["summary"]["focas_available"] is True
    assert any(p["port"] == 23 for p in result["other_ports"])


def test_get_port_name():
    detector = ProtocolDetector("10.0.0.1")
    assert detector._get_port_name(23) == "Telnet"
    assert "12345" in detector._get_port_name(12345)


@pytest.mark.asyncio
async def test_check_system_files_focas_hint():
    detector = ProtocolDetector("10.0.0.1")
    ftp = MagicMock()

    async def get_system_file(name):
        if name == "VER.NC":
            return "X" * 50 + " FOCAS " + "Y" * 200
        raise FileNotFoundError("missing")

    ftp.get_system_file = get_system_file
    result = await detector.check_system_files(ftp)
    assert len(result["ver_nc"]["preview"]) == 200
    assert any("FOCAS" in h for h in result["hints"])


@pytest.mark.asyncio
async def test_detect_protocols_without_clients():
    with patch.object(ProtocolDetector, "detect_all", return_value={"summary": {}}):
        result = await detect_protocols("10.0.0.1")
    assert "system_files" not in result
    assert "http_endpoints" not in result


@pytest.mark.asyncio
async def test_detect_protocols_ftp_error():
    ftp = MagicMock()

    async def boom(*_a, **_k):
        raise RuntimeError("ftp down")

    with patch.object(ProtocolDetector, "detect_all", return_value={"summary": {}}):
        with patch.object(ProtocolDetector, "check_system_files", side_effect=boom):
            result = await detect_protocols("10.0.0.1", ftp_client=ftp)
    assert "error" in result["system_files"]
