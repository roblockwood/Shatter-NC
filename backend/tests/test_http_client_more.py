"""Additional HTTP client parser / connection tests."""
from unittest.mock import patch

from app.clients.http_client import CNCHttpClient


def test_parse_tool_data_row():
    html = """
    <table>
      <tr><td>Pot</td><td>Tool No.</td><td>Tool name</td></tr>
      <tr>
        <td>1</td><td>5</td><td>.250 ENDMILL</td>
        <td>3.5x 0.25</td><td>1</td><td>9952mi</td><td>STD Tool</td>
        <td class="bg_red">R</td>
      </tr>
      <tr><td>2</td><td></td><td></td></tr>
      <tr><td>3</td><td>abc</td><td>bad</td></tr>
    </table>
    """
    data = CNCHttpClient("10.0.0.1")._parse_tool_data(html, units="in")
    assert data["units"] == "in"
    assert any(t.get("tool_number") == 5 for t in data["tools"])
    tool = next(t for t in data["tools"] if t.get("tool_number") == 5)
    assert tool["length"] == 3.5
    assert tool["diameter"] == 0.25
    assert tool["life"] == 9952


def test_test_connection_success_and_fail():
    client = CNCHttpClient("10.0.0.1")
    with patch.object(client, "_send_request", return_value="<html>ok</html>"):
        result = client.test_connection()
        assert result["success"] is True
        assert "latency_ms" in result or result.get("success")

    with patch.object(client, "_send_request", return_value=""):
        result = client.test_connection()
        assert result["success"] is False


def test_get_status_overview_error_path():
    client = CNCHttpClient("10.0.0.1")
    with patch.object(client, "get_running_log", return_value={"error": "down"}):
        try:
            client.get_status_overview()
            assert False, "expected ConnectionError"
        except ConnectionError as e:
            assert "running log" in str(e).lower()


def test_get_status_overview_happy():
    client = CNCHttpClient("10.0.0.1")
    with patch.object(client, "get_running_log", return_value={"program_name": "O1", "status": "Idle"}):
        with patch.object(client, "get_work_counter", return_value={"counters": []}):
            with patch.object(client, "get_alarm_log", return_value={"alarms": []}):
                overview = client.get_status_overview()
    assert overview["program_name"] == "O1"
    assert overview["ip_address"] == "10.0.0.1"
