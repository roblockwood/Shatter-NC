from app.services.unified_tool_view import build_unified_tool_view


def test_tool_centric_rows_without_atc():
    toln = [
        {"tool_number": 1, "tool_name": "EM", "length": 2.0, "diameter": 0.5, "life": 100},
        {"tool_number": 5, "tool_name": "DRILL", "length": 1.0, "diameter": 0.25, "life": 50},
    ]
    view = build_unified_tool_view(toln, None)

    assert view["atc_available"] is False
    assert len(view["tools"]) == 2
    assert view["empty_pockets"] == []
    assert view["tools"][0]["in_atc"] is False
    assert "pot_number" not in view["tools"][0]


def test_atc_fields_only_when_assigned():
    toln = [
        {"tool_number": 5, "tool_name": "EM", "length": 2.0, "diameter": 0.5, "life": 100},
        {"tool_number": 10, "tool_name": "PROBE", "length": 1.0, "diameter": 0.1, "life": 0},
    ]
    atc = {
        "tools": [
            {"pot_number": "SPINDLE", "tool_number": 5, "tool_type": 1, "color": 0},
            {"pot_number": 1, "tool_number": 5, "tool_type": 1, "color": 2, "group": 1},
            {"pot_number": 2, "tool_number": 0, "tool_type": 1, "color": 0},
            {"pot_number": 3, "tool_number": 255, "tool_type": 1, "color": 0},
        ]
    }

    view = build_unified_tool_view(toln, atc)

    assert view["atc_available"] is True
    assert view["spindle"]["tool_number"] == 5
    assert len(view["empty_pockets"]) == 2
    assert view["empty_pockets"][0]["pot_number"] == 2

    assigned = next(t for t in view["tools"] if t["tool_number"] == 5)
    unassigned = next(t for t in view["tools"] if t["tool_number"] == 10)

    assert assigned["in_atc"] is True
    assert assigned["pot_number"] == 1
    assert assigned["color"] == 2

    assert unassigned["in_atc"] is False
    assert "pot_number" not in unassigned
