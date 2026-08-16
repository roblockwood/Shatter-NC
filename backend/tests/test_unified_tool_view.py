from app.services.unified_tool_view import (
    build_unified_tool_view,
    expand_atc_parsed_to_pocket_count,
)


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


def test_expand_atc_to_configured_pocket_count():
    atc = {
        "tools": [
            {"pot_number": 1, "tool_number": 5, "tool_type": 1, "color": 2},
            {"pot_number": 3, "tool_number": 0, "tool_type": 1, "color": 0},
        ]
    }

    expanded = expand_atc_parsed_to_pocket_count(atc, 5)
    pots = [
        row["pot_number"]
        for row in expanded["tools"]
        if isinstance(row.get("pot_number"), int)
    ]

    assert pots == [1, 2, 3, 4, 5]
    assert expanded["tools"][1]["tool_number"] == 0  # synthetic empty pot 2


def test_unified_view_uses_atc_pockets_for_empty_list():
    atc = {
        "tools": [
            {"pot_number": 1, "tool_number": 5, "tool_type": 1, "color": 2},
        ]
    }
    view = build_unified_tool_view([], atc, atc_pockets=4)

    assert len(view["empty_pockets"]) == 3
    assert {p["pot_number"] for p in view["empty_pockets"]} == {2, 3, 4}
