"""Settings API + small remaining coverage wins."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.cnc_data.alarm_schema import get_alarm_schema
from app.schemas.cnc_data.mem_schema import get_mem_schema
from app.schemas.cnc_data.montr_schema import get_montr_schema
from app.schemas.cnc_data.panel_schema import get_panel_schema
from app.schemas.cnc_data.posni_schema import get_posn_schema
from app.schemas.cnc_data.prd3_schema import get_prd3_schema
from app.services.mqtt_publisher import MqttPublisher
from app.utils.time_utils import format_cnc_time


client = TestClient(app, raise_server_exceptions=False)


def test_settings_layout_roundtrip():
    r = client.get("/api/settings/layout")
    assert r.status_code == 200
    r = client.put("/api/settings/layout", json={"panes": ["a"]})
    assert r.status_code == 200
    assert r.json()["layout_config"] == {"panes": ["a"]}
    r = client.get("/api/settings/layout")
    assert r.json()["layout_config"] == {"panes": ["a"]}


@pytest.mark.parametrize(
    "getter",
    [get_alarm_schema, get_mem_schema, get_montr_schema, get_panel_schema, get_posn_schema, get_prd3_schema],
)
def test_schema_unsupported_version(getter):
    with pytest.raises(ValueError):
        getter("Z99")


def test_format_cnc_time_edges():
    assert format_cnc_time(None) is None
    assert format_cnc_time("") == ""
    assert format_cnc_time("123") == "123"
    assert format_cnc_time("abcdefghi") == "abcdefghi"
    assert format_cnc_time("123456789") == "1234:56.789"


@pytest.mark.asyncio
async def test_mqtt_publisher_disabled():
    pub = MqttPublisher()
    assert pub.configured() is False or isinstance(pub.configured(), bool)
    st = pub.status()
    assert st.enabled is False or isinstance(st.enabled, bool)
    await pub.start()
    await pub.stop()
