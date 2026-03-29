"""Sidecar JSON → compressor_status payload mapping."""
from datetime import datetime, timezone

from app.integrations.kaeser_sc2.sidecar_mapper import build_compressor_status_payload, infer_status


def test_build_status_offline_no_data():
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    p = build_compressor_status_payload(
        compressor_id=1,
        compressor_name="C1",
        ip_address="192.168.1.10",
        enabled=True,
        poll_interval_seconds=5,
        sidecar_rest_base_url="http://sidecar:3004",
        mqtt_topic_root="k1",
        operational=None,
        rest_bundle=None,
        rest_error="connection refused",
        last_operational_mqtt_at=None,
        poll_timestamp=now,
        response_time_ms=10,
    )
    assert p["is_online"] is False
    assert p["status"] == "offline"
    assert "error" in p


def test_build_status_from_operational():
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    op = {
        "powerState": "on",
        "compressorState": "load",
        "startMode": "remote",
        "pressure": {"value": 100.0, "unit": "psi"},
    }
    p = build_compressor_status_payload(
        compressor_id=2,
        compressor_name="C2",
        ip_address="192.168.1.11",
        enabled=True,
        poll_interval_seconds=5,
        sidecar_rest_base_url="http://sidecar:3004",
        mqtt_topic_root="k2",
        operational=op,
        rest_bundle={"messages": [{"messageType": "Warning", "messageId": 49, "message": "Test"}]},
        rest_error=None,
        last_operational_mqtt_at=now,
        poll_timestamp=now,
        response_time_ms=5,
    )
    assert p["is_online"] is True
    assert p["status"] == "load"
    assert p["metrics"]["operational"] == op
    assert len(p["alarms"]) == 1
    assert p["alarms"][0]["code"] == "49"


def test_infer_compressor_running_is_load():
    assert (
        infer_status({"powerState": "on", "compressorState": "compressor running"})
        == "load"
    )


def test_infer_no_load_is_idle():
    assert infer_status({"powerState": "on", "compressorState": "no load"}) == "idle"


def test_infer_unload_is_idle():
    assert infer_status({"powerState": "on", "compressorState": "unload"}) == "idle"


def test_infer_on_load_string():
    assert infer_status({"powerState": "on", "compressorState": "on load"}) == "load"


def test_infer_download_not_load():
    assert infer_status({"powerState": "on", "compressorState": "download update"}) != "load"


def test_infer_led_load_overrides_stale_compressor_state():
    op = {"powerState": "on", "compressorState": "compressor running"}
    led = {"load": True, "idle": False}
    assert infer_status(op, led) == "load"


def test_infer_led_idle_overrides_compressor_running_text():
    op = {"powerState": "on", "compressorState": "compressor running"}
    led = {"idle": True, "load": False}
    assert infer_status(op, led) == "idle"


def test_infer_led_nested_led_data_key():
    op = {"powerState": "on", "compressorState": "ready"}
    led = {"led-data": {"load": True}}
    assert infer_status(op, led) == "load"


def test_infer_power_off_ignores_led():
    op = {"powerState": "off", "compressorState": "compressor running"}
    led = {"load": True}
    assert infer_status(op, led) == "stopped"


def test_build_status_uses_led_from_rest_bundle():
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    op = {"powerState": "on", "compressorState": "compressor running"}
    p = build_compressor_status_payload(
        compressor_id=3,
        compressor_name="C3",
        ip_address="192.168.1.12",
        enabled=True,
        poll_interval_seconds=5,
        sidecar_rest_base_url="http://sidecar:3004",
        mqtt_topic_root="k3",
        operational=op,
        rest_bundle={"led_data": {"idle": True, "load": False}},
        rest_error=None,
        last_operational_mqtt_at=now,
        poll_timestamp=now,
        response_time_ms=3,
    )
    assert p["status"] == "idle"
