"""Tests for Blum probe catalog resolution and validation."""
import json
from pathlib import Path

import pytest

from app.services.probe_catalog import (
    ProbeCatalogError,
    catalog_for_api,
    get_poison_values,
    load_probe_catalog,
    resolve_routine,
    validate_run_params,
    validate_wcs,
)

BACKEND_CATALOG = Path(__file__).resolve().parents[1] / "app" / "data" / "probe_catalog.json"
FRONTEND_CATALOG = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "probe_catalog.json"
)


def test_catalog_loads():
    cat = load_probe_catalog()
    assert cat["version"] == 1
    assert len(cat["routines"]) >= 20
    assert "900" in cat["poison"]


def test_backend_frontend_catalog_parity():
    assert FRONTEND_CATALOG.is_file(), f"missing {FRONTEND_CATALOG}"
    backend = json.loads(BACKEND_CATALOG.read_text(encoding="utf-8"))
    frontend = json.loads(FRONTEND_CATALOG.read_text(encoding="utf-8"))
    assert backend == frontend


def test_resolve_corner_xyz_probe():
    resolved = resolve_routine("corner_xyz", "probe")
    assert resolved["program"] == 8110
    assert resolved["macros"] == ["900", "901", "902", "903"]


def test_resolve_diameter_inside_measure():
    resolved = resolve_routine("diameter_inside", "measure")
    assert resolved["program"] == 8216
    assert resolved["macros"] == ["900", "904"]


def test_tool_length_probe_only():
    resolved = resolve_routine("tool_length", "probe")
    assert resolved["program"] == 8100
    with pytest.raises(ProbeCatalogError):
        resolve_routine("tool_length", "measure")


def test_validate_run_params_ok():
    _, writes = validate_run_params(
        "corner_xyz",
        "probe",
        {"900": 59, "901": -0.3, "902": -0.3, "903": -0.25},
    )
    assert writes[900] == 59.0
    assert writes[901] == -0.3


def test_validate_run_params_accepts_field_keys():
    _, writes = validate_run_params(
        "diameter_inside",
        "probe",
        {"wcs": 54, "size": 50.8},
    )
    assert writes[900] == 54.0
    assert writes[904] == 50.8


def test_validate_rejects_fractional_wcs():
    with pytest.raises(ProbeCatalogError, match="whole number"):
        validate_run_params(
            "corner_xyz",
            "probe",
            {"900": 54.5, "901": -3, "902": -3, "903": -5},
        )


def test_validate_rejects_poison_wcs():
    with pytest.raises(ProbeCatalogError, match="poison"):
        validate_run_params("single_face_z", "probe", {"900": 0})


def test_validate_wcs_rules():
    assert validate_wcs(54) is None
    assert validate_wcs(-1) is None
    assert validate_wcs(0) is not None
    assert validate_wcs(60) is not None
    assert validate_wcs(54.5) is not None


def test_validate_rejects_missing_and_extra():
    with pytest.raises(ProbeCatalogError, match="Missing"):
        validate_run_params("corner_xy", "probe", {"900": 54, "901": 1})
    with pytest.raises(ProbeCatalogError, match="Unexpected"):
        validate_run_params(
            "single_face_x_plus",
            "probe",
            {"900": 54, "901": 1},
        )


def test_three_point_macros():
    resolved = resolve_routine("three_point_outside", "probe")
    assert resolved["program"] == 8122
    assert resolved["macros"] == ["900", "903", "904", "905", "906", "907"]


def test_poison_values():
    poison = get_poison_values()
    assert poison[900] == 0
    assert poison[901] == 999
    assert poison[920] == 0


def test_catalog_for_api_shape():
    payload = catalog_for_api()
    assert "routines" in payload
    assert "categories" in payload
    assert "fields" in payload
    assert payload.get("gate_program") == 8099
    assert payload.get("target_macro") == 908


def test_poison_includes_target_macro():
    poison = get_poison_values()
    assert poison[908] == 0


def test_obstacle_r_negated_on_write():
    """O8702 inside+Z needs R < 0; UI enters positive clearance."""
    _, writes = validate_run_params(
        "obstacle_inside_dia",
        "probe",
        {"900": 54, "903": -5, "904": 40, "905": 8},
    )
    assert writes[905] == -8.0
    # Already-negative values stay negative (not double-flipped)
    _, writes2 = validate_run_params(
        "obstacle_inside_dia",
        "probe",
        {"900": 54, "903": -5, "904": 40, "905": -6},
    )
    assert writes2[905] == -6.0
