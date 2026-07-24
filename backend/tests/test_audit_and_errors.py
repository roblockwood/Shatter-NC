"""Audit logger and remaining small coverage wins."""
from app.services.audit_logger import AuditLogger
from app.utils.api_errors import public_error_detail


def test_audit_logger_success_and_failure():
    AuditLogger.log_tool_modification(
        machine_id=1,
        operation_type="tool_color",
        operation_details={"pot_number": 1},
        success=True,
    )
    AuditLogger.log_tool_modification(
        machine_id=1,
        operation_type="tool_color",
        operation_details={"pot_number": 1},
        success=False,
        error_message="nope",
        machine_state={"status": "standby"},
    )


def test_api_errors_public_detail(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "LOG_LEVEL", "INFO")
    assert public_error_detail(Exception("secret")) == "Request failed"
    monkeypatch.setattr(config.settings, "LOG_LEVEL", "DEBUG")
    assert "secret" in public_error_detail(Exception("secret"))
