"""Tests for ATC optimizer pure functions."""
import pytest

from app.services.atc_optimizer import optimize_atc, rotary_distance


def test_rotary_distance():
    assert rotary_distance(1, 2, 21) == 1
    assert rotary_distance(1, 21, 21) == 1
    assert rotary_distance(1, 11, 21) == 10
    assert rotary_distance(5, 5, 21) == 0


def test_optimize_empty_sequence():
    result = optimize_atc([])
    assert result["unique_tools"] == []
    assert result["baseline_cost"] == 0
    assert result["optimized_cost"] == 0
    assert result["improvement_pct"] == 0.0


def test_optimize_single_tool():
    result = optimize_atc([7, 7, 7], num_pockets=21, random_seed=0)
    assert result["unique_tools"] == [7]
    assert result["tool_change_count"] == 0
    assert result["baseline_cost"] == 0
    assert result["optimized_cost"] == 0


def test_too_many_tools_raises():
    with pytest.raises(ValueError, match="pockets"):
        optimize_atc([1, 2, 3], num_pockets=2)


def test_optimize_improves_or_matches_baseline():
    result = optimize_atc(
        [1, 2, 1, 2, 1, 2],
        num_pockets=21,
        random_seed=0,
        sa_iterations=2000,
    )
    assert "T1→T2" in result["transition_matrix"]
    assert "T2→T1" in result["transition_matrix"]
    assert result["optimized_cost"] <= result["baseline_cost"]
    assert result["tool_change_count"] == 5


def test_pinned_tools_respected():
    result = optimize_atc(
        [1, 2, 3, 1, 2],
        num_pockets=21,
        random_seed=0,
        sa_iterations=1000,
        pinned_tools={1: 10},
    )
    opt = result["optimized_assignment"]
    # Keys may be str or int depending on path
    pot = opt.get(1, opt.get("1"))
    assert pot == 10


def test_tool_change_count_ignores_repeats():
    result = optimize_atc([1, 1, 2, 2, 1], num_pockets=21, random_seed=0, sa_iterations=500)
    assert result["tool_change_count"] == 2
