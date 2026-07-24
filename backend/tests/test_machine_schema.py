"""Tests for machine response schema redaction."""
from datetime import datetime, timezone

from app.schemas.machine import MachineResponse


def test_machine_response_excludes_ftp_password_from_json():
    response = MachineResponse(
        id=1,
        name="Mill 1",
        ip_address="192.168.1.100",
        ftp_username="cnc",
        ftp_password="supersecret",
        created_at=datetime.now(timezone.utc),
    )
    payload = response.model_dump()
    assert "ftp_password" not in payload
    assert payload["ftp_credentials_configured"] is True
