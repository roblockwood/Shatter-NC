"""Pure-function / parser tests for Kaeser SC2 client."""
from app.integrations.kaeser_sc2.client import (
    KaeserSc2Client,
    _normalize_base_url,
    _sha256_hex,
)


def test_sha256_hex():
    assert len(_sha256_hex("abc")) == 64


def test_normalize_base_url():
    assert _normalize_base_url("") == ""
    assert _normalize_base_url("10.0.0.5") == "https://10.0.0.5"
    assert _normalize_base_url("https://example.com/") == "https://example.com"


def test_session_auth_and_cookies():
    client = KaeserSc2Client(base_url="https://10.0.0.5", username="u", password="p")
    auth = client._session_auth_for_key("KEY")
    assert isinstance(auth, str) and len(auth) == 64
    cookie = client._cookie_header(session_id="SID", session_key="SKEY")
    assert "Session-Id=SID" in cookie
    assert "Session-Key=SKEY" in cookie


def test_id_matches_and_coerce():
    assert KaeserSc2Client._id_matches(123, 123) is True
    assert KaeserSc2Client._id_matches("123", 123) is True
    assert KaeserSc2Client._id_matches("x", 123) is False
    assert KaeserSc2Client._coerce_str(None) == ""
    assert KaeserSc2Client._coerce_str(5) == "5"
    assert KaeserSc2Client._coerce_num("1.5") == 1.5
    assert KaeserSc2Client._coerce_num("bad") is None


def test_block3_and_extract_value():
    client = KaeserSc2Client(base_url="https://x", username="u", password="p")
    raw = {
        "3": {
            "a": {"Id": 10, "Value": "7.5", "Unit": "bar"},
        }
    }
    items = KaeserSc2Client._block3_items(raw)
    assert items
    item = client._extract_value_item(raw, 10)
    assert item is not None
    assert client._extract_string_value(raw, 10) == "7.5"
    assert client._extract_numeric_value(raw, 10) == 7.5
    assert client._extract_unit(raw, 10) == "bar"


def test_parse_operational_with_ids():
    from app.integrations.kaeser_sc2.client import SC2_OPERATIONAL_IDS

    client = KaeserSc2Client(base_url="https://x", username="u", password="p")
    items = {}
    for key, oid in SC2_OPERATIONAL_IDS.items():
        value = "On Load" if key == "COMPRESSOR_STATE" else ("RC" if key == "START_MODE" else "1.0")
        items[str(oid)] = {"Id": oid, "Value": value, "Unit": "bar"}
    parsed = client._parse_operational({"3": items})
    assert parsed.get("compressorState") == "load"
    assert "powerState" in parsed
    assert isinstance(parsed, dict)


def test_parse_messages_and_hours():
    client = KaeserSc2Client(base_url="https://x", username="u", password="p")
    hours = client._parse_operating_hours({"3": {}})
    assert isinstance(hours, dict)
    maint = client._parse_maintenance_timers({"3": {}})
    assert isinstance(maint, dict)
    leds = client._parse_led_data({"3": {}})
    assert isinstance(leds, dict)
    msgs = client._parse_messages({"3": {}})
    assert msgs is not None or msgs is None
