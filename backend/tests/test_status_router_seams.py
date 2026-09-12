"""Seam-level tests for app.api.status.

These tests lock in the public interface of the status router so that a
split into sub-modules can be verified without requiring a running DB or
live machine connection.

Tests cover:
  - router object is an APIRouter and all expected routes are registered
  - Pydantic models are importable with the expected fields
  - set_polling_service / polling_service injection works at module level
  - ColorChangeRequest / BatchColorChangeRequest / response models exist
"""
import types
from fastapi import APIRouter
from pydantic import BaseModel

import app.api.status as status_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route_signatures(router: APIRouter) -> set:
    """Return {(frozenset(methods), path)} for every route on the router.

    FastAPI 0.139+/Starlette 1.x stores nested ``include_router`` entries as
    ``_IncludedRouter`` wrappers, so we walk ``original_router`` recursively.
    """
    sigs = set()

    def walk(node) -> None:
        for route in getattr(node, "routes", []) or []:
            if hasattr(route, "methods") and hasattr(route, "path"):
                sigs.add((frozenset(route.methods), route.path))
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(nested)

    walk(router)
    return sigs


# ---------------------------------------------------------------------------
# Module-level interface
# ---------------------------------------------------------------------------

def test_router_is_api_router():
    """status.router must be an APIRouter (not a plain object)."""
    assert isinstance(status_module.router, APIRouter)


def test_set_polling_service_exists_and_is_callable():
    """set_polling_service must be a callable that sets the module global."""
    assert callable(status_module.set_polling_service)


def test_polling_service_injection():
    """set_polling_service updates the module-level polling_service global."""
    sentinel = object()
    status_module.set_polling_service(sentinel)
    assert status_module.polling_service is sentinel
    # Restore to None so other tests/imports are not affected
    status_module.set_polling_service(None)


# ---------------------------------------------------------------------------
# Route registration - read-only endpoints
# ---------------------------------------------------------------------------

def test_status_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/status") in sigs


def test_running_log_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/running-log") in sigs


def test_counters_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/counters") in sigs


def test_alarms_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/alarms/live") in sigs


def test_position_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/position") in sigs


# ---------------------------------------------------------------------------
# Route registration - tool endpoints
# ---------------------------------------------------------------------------

def test_get_tools_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/tools") in sigs


def test_refresh_tool_data_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/status/tools/refresh") in sigs


def test_change_tool_color_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/atc/pot/{pot_number}/color") in sigs


def test_batch_change_tool_colors_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/atc/colors/batch") in sigs


def test_batch_apply_tool_changes_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/changes/batch") in sigs


def test_change_tool_assignment_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/atc/pot/{pot_number}/tool") in sigs


def test_change_tool_type_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/atc/pot/{pot_number}/type") in sigs


def test_delete_tool_from_pot_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"DELETE"}), "/{machine_id}/tools/atc/pot/{pot_number}") in sigs


def test_change_spindle_tool_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/spindle") in sigs


def test_set_tool_life_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/{tool_number}/life") in sigs


def test_set_tool_offset_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/{tool_number}/offset") in sigs


def test_set_macro_variable_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/macros/{macro_number}") in sigs


def test_set_measurement_tool_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"PUT"}), "/{machine_id}/tools/measurement-tool") in sigs


def test_probe_catalog_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/probe/catalog") in sigs


def test_probe_write_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/write") in sigs


def test_probe_start_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/start") in sigs


def test_probe_poison_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/poison") in sigs


def test_probe_collect_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/collect") in sigs


def test_probe_exclusive_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/exclusive") in sigs


def test_probe_tool_batch_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/probe/tool-batch") in sigs


# ---------------------------------------------------------------------------
# Route registration - file endpoints
# ---------------------------------------------------------------------------

def test_list_programs_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/programs") in sigs


def test_download_file_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/download") in sigs


def test_get_file_metadata_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/metadata") in sigs


def test_view_file_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"GET"}), "/{machine_id}/view") in sigs


def test_upload_file_route_registered():
    sigs = _route_signatures(status_module.router)
    assert (frozenset({"POST"}), "/{machine_id}/upload") in sigs


# ---------------------------------------------------------------------------
# Route count sanity check
# ---------------------------------------------------------------------------

def test_total_route_count():
    """Exactly 30 routes must be registered. Catches silent deletions during split."""
    sigs = _route_signatures(status_module.router)
    assert len(sigs) == 30, f"Expected 30 routes, got {len(sigs)}: {sigs}"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

def test_color_change_request_fields():
    """ColorChangeRequest must have pot_number, tool_number, color."""
    m = status_module.ColorChangeRequest(pot_number=1, tool_number=5, color=2)
    assert m.pot_number == 1
    assert m.tool_number == 5
    assert m.color == 2


def test_batch_color_change_request_holds_list():
    """BatchColorChangeRequest wraps a list of ColorChangeRequest."""
    m = status_module.BatchColorChangeRequest(
        changes=[
            status_module.ColorChangeRequest(pot_number=1, tool_number=5, color=2),
        ]
    )
    assert len(m.changes) == 1


def test_color_change_result_fields():
    """ColorChangeResult must have success, pot_number, tool_number, color."""
    r = status_module.ColorChangeResult(pot_number=1, tool_number=5, color=2, success=True)
    assert r.success is True
    assert r.error_code is None


def test_batch_color_change_response_fields():
    """BatchColorChangeResponse must have results, total, successful, failed."""
    resp = status_module.BatchColorChangeResponse(
        results=[], total=0, successful=0, failed=0
    )
    assert resp.total == 0
    assert isinstance(resp.results, list)
