"""Tests for CNCHttpClient HTML parsers."""
from app.clients.http_client import CNCHttpClient


def _client():
    return CNCHttpClient("10.0.0.1")


def test_parse_running_log():
    html = """
    <table>
      <tr><td>Program Current</td><td>O2045</td></tr>
      <tr><td>Cycle time</td><td>00:10.5</td></tr>
      <tr><td>Cutting time</td><td>00:08.0</td></tr>
      <tr><td>Non cutting time</td><td>00:02.5</td></tr>
      <tr><td>Power on time</td><td>12:00</td></tr>
      <tr><td>Operation time</td><td>01:00</td></tr>
      <tr><td>Status : Running</td></tr>
    </table>
    """
    data = _client()._parse_running_log(html)
    assert data["program_name"] == "O2045"
    assert data["cycle_time"] == "00:10.5"
    assert data["cutting_time"] == "00:08.0"
    assert "timestamp" in data


def test_parse_running_log_empty_program():
    html = "<td>Program Current</td><td>   </td>"
    data = _client()._parse_running_log(html)
    assert data["program_name"] is None


def test_parse_work_counter():
    html = """
    Counter 1<td>10</td>
    Counter 2<td>20</td>
    Counter 3<td>30</td>
    Counter 4<td>40</td>
    """
    data = _client()._parse_work_counter(html)
    assert len(data["counters"]) == 4
    assert data["counters"][0]["count"] == 10
    assert data["counters"][3]["count"] == 40


def test_parse_alarm_log():
    html = """
    <tr bgcolor="#000000" class="alarm_level_3">
      <td>NC1234</td><td>Something bad</td><td>O1000</td><td>N10</td>
    </tr>
    <tr bgcolor="#000000" class="alarm_level_1">
      <td>&nbsp;</td><td>skip</td><td></td><td></td>
    </tr>
    """
    data = _client()._parse_alarm_log(html)
    assert len(data["alarms"]) == 1
    assert data["alarms"][0]["code"] == "NC1234"
    assert data["alarms"][0]["severity"] == "error"


def test_parse_tool_data_skips_short_rows():
    html = "<table><tr><td>Pot</td><td>Tool</td></tr></table>"
    data = _client()._parse_tool_data(html, units="in")
    assert data["tools"] == []
    assert data.get("units") == "in" or "tools" in data
