from app.services.atc_tool_merge import merge_atc_tools_for_display


def test_merge_includes_empty_and_cap_pockets():
    atc_parsed = {
        "tools": [
            {"pot_number": "SPINDLE", "tool_number": 3, "tool_type": 1, "color": 0},
            {"pot_number": 1, "tool_number": 5, "tool_type": 1, "color": 2},
            {"pot_number": 2, "tool_number": 0, "tool_type": 1, "color": 0},
            {"pot_number": 3, "tool_number": 255, "tool_type": 1, "color": 0},
        ]
    }
    tool_table = [
        {
            "tool_number": 5,
            "tool_name": "EM",
            "diameter": 0.5,
            "length": 2.0,
        }
    ]

    merged = merge_atc_tools_for_display(atc_parsed, tool_table)

    assert merged[0]["pot_number"] == "SPINDLE"
    assert merged[0]["tool_number"] == 3
    assert merged[1] == {
        "pot_number": 1,
        "tool_number": 5,
        "tool_name": "EM",
        "diameter": 0.5,
        "length": 2.0,
        "group": None,
        "life": None,
        "tool_type": 1,
        "color": 2,
    }
    assert merged[2]["pot_number"] == 2
    assert merged[2]["tool_number"] == 0
    assert merged[3]["pot_number"] == 3
    assert merged[3]["tool_number"] == 0


def test_merge_tool_without_toln_still_shown():
    atc_parsed = {
        "tools": [
            {"pot_number": 4, "tool_number": 9, "tool_type": 2, "color": 1},
        ]
    }

    merged = merge_atc_tools_for_display(atc_parsed, [])

    assert len(merged) == 1
    assert merged[0]["pot_number"] == 4
    assert merged[0]["tool_number"] == 9
    assert merged[0]["tool_name"] is None
