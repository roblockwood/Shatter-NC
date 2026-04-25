"""Seam-level tests for app.api.programs.

These tests lock in the public interface of the programs router so that a
split into sub-modules can be verified without requiring a running DB or
live machine connection.

Tests cover:
  - router object is an APIRouter and all expected routes are registered
  - All Pydantic models are importable with the expected fields
  - Private helper functions are importable
"""
from fastapi import APIRouter
from pydantic import BaseModel

import app.api.programs as programs_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route_signatures(router: APIRouter) -> set:
    """Return {(frozenset(methods), path)} for every route on the router."""
    sigs = set()
    for route in router.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            sigs.add((frozenset(route.methods), route.path))
    return sigs


# ---------------------------------------------------------------------------
# Module-level interface
# ---------------------------------------------------------------------------

def test_router_is_api_router():
    """programs.router must be an APIRouter."""
    assert isinstance(programs_module.router, APIRouter)


def test_router_has_routes():
    """programs.router must have at least 13 routes registered."""
    assert len(programs_module.router.routes) >= 13


# ---------------------------------------------------------------------------
# Pydantic models — validation
# ---------------------------------------------------------------------------

def test_program_validate_request_importable():
    assert issubclass(programs_module.ProgramValidateRequest, BaseModel)
    assert "gcode_content" in programs_module.ProgramValidateRequest.model_fields


def test_tool_validation_result_importable():
    assert issubclass(programs_module.ToolValidationResult, BaseModel)
    expected_fields = {
        "tool_number", "required_diameter", "required_length",
        "available", "diameter_match", "length_sufficient",
    }
    for field in expected_fields:
        assert field in programs_module.ToolValidationResult.model_fields, (
            f"ToolValidationResult missing field: {field}"
        )


def test_wcs_validation_result_importable():
    assert issubclass(programs_module.WCSValidationResult, BaseModel)
    expected_fields = {"valid", "work_offset", "expected", "actual", "within_tolerance"}
    for field in expected_fields:
        assert field in programs_module.WCSValidationResult.model_fields, (
            f"WCSValidationResult missing field: {field}"
        )


def test_program_validation_response_importable():
    assert issubclass(programs_module.ProgramValidationResponse, BaseModel)
    expected_fields = {"valid", "tools", "wcs_offset", "warnings", "errors", "metadata"}
    for field in expected_fields:
        assert field in programs_module.ProgramValidationResponse.model_fields, (
            f"ProgramValidationResponse missing field: {field}"
        )


def test_program_validation_with_content_response_importable():
    assert issubclass(programs_module.ProgramValidationWithContentResponse, BaseModel)
    assert "validation" in programs_module.ProgramValidationWithContentResponse.model_fields
    assert "gcode_content" in programs_module.ProgramValidationWithContentResponse.model_fields


def test_deploy_validated_request_importable():
    assert issubclass(programs_module.DeployValidatedRequest, BaseModel)
    expected_fields = {"deployed_filename", "gcode_content", "validation_results"}
    for field in expected_fields:
        assert field in programs_module.DeployValidatedRequest.model_fields


# ---------------------------------------------------------------------------
# Pydantic models — ATC optimizer
# ---------------------------------------------------------------------------

def test_atc_optimize_request_importable():
    assert issubclass(programs_module.ATCOptimizeRequest, BaseModel)
    expected_fields = {"gcode_content", "num_pockets", "current_assignment", "pinned_tools"}
    for field in expected_fields:
        assert field in programs_module.ATCOptimizeRequest.model_fields


def test_atc_optimize_response_importable():
    assert issubclass(programs_module.ATCOptimizeResponse, BaseModel)
    expected_fields = {
        "tool_sequence", "unique_tools", "tool_change_count", "transition_matrix",
        "baseline_assignment", "optimized_assignment", "baseline_cost", "optimized_cost",
        "improvement_pct",
    }
    for field in expected_fields:
        assert field in programs_module.ATCOptimizeResponse.model_fields, (
            f"ATCOptimizeResponse missing field: {field}"
        )


def test_atc_assignment_entry_importable():
    assert issubclass(programs_module.ATCAssignmentEntry, BaseModel)
    assert "tool_number" in programs_module.ATCAssignmentEntry.model_fields
    assert "pot" in programs_module.ATCAssignmentEntry.model_fields


# ---------------------------------------------------------------------------
# Private helpers — importable
# ---------------------------------------------------------------------------

def test_validate_tool_helper_importable():
    """_validate_tool must be accessible from the programs module."""
    assert callable(programs_module._validate_tool)


def test_validate_wcs_offset_helper_importable():
    """_validate_wcs_offset must be accessible from the programs module."""
    assert callable(programs_module._validate_wcs_offset)


# ---------------------------------------------------------------------------
# Route registration — validation routes
# ---------------------------------------------------------------------------

def test_validate_program_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/machines/{machine_id}/programs/validate") in sigs


def test_validate_file_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/machines/{machine_id}/programs/validate-file") in sigs


# ---------------------------------------------------------------------------
# Route registration — program library routes
# ---------------------------------------------------------------------------

def test_list_programs_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "") in sigs


def test_get_program_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/{program_id}") in sigs


def test_get_program_versions_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/by-filename/{filename}") in sigs


def test_upload_program_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/upload") in sigs


def test_deploy_validated_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/machines/{machine_id}/programs/deploy-validated") in sigs


# ---------------------------------------------------------------------------
# Route registration — deployment management routes
# ---------------------------------------------------------------------------

def test_deploy_program_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/{program_id}/deploy") in sigs


def test_list_machine_deployments_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/machines/{machine_id}/deployments") in sigs


def test_list_program_deployments_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/{program_id}/deployments") in sigs


def test_get_deployment_by_onumber_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/machines/{machine_id}/deployments/by-onumber/{onumber}") in sigs


def test_get_deployment_by_id_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/deployments/{deployment_id}") in sigs


def test_next_onumber_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"GET"}), "/machines/{machine_id}/next-onumber") in sigs


# ---------------------------------------------------------------------------
# Route registration — ATC optimizer
# ---------------------------------------------------------------------------

def test_analyze_atc_route_registered():
    sigs = _route_signatures(programs_module.router)
    assert (frozenset({"POST"}), "/analyze-atc") in sigs
