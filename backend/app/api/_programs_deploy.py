"""Deployment management routes.

Routes:
    POST /{program_id}/deploy                                     — deploy existing program to machine
    GET  /machines/{machine_id}/deployments                       — list machine deployments
    GET  /{program_id}/deployments                                — list deployments of a program
    GET  /machines/{machine_id}/deployments/by-onumber/{onumber}  — get deployment by O-number
    GET  /deployments/{deployment_id}                             — get deployment by ID
    PATCH /deployments/{deployment_id}/validation                  — overwrite stored validation results
    GET  /machines/{machine_id}/next-onumber                       — FIFO O-number allocation
"""

import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Any, Optional, List

from app.db.base import get_db
from app.models.machine import Machine
from app.models.program import Program, ProgramDeployment
from app.schemas.program import (
    ProgramDeploymentCreate,
    ProgramDeploymentResponse,
)
from app.services.program_service import ProgramService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{program_id}/deploy", response_model=ProgramDeploymentResponse)
async def deploy_program(
    program_id: int,
    request: ProgramDeploymentCreate,
    db: Session = Depends(get_db),
):
    """
    Deploy an existing program to a machine.

    This creates a deployment record linking the program to the machine with the specified O-number.
    """
    try:
        service = ProgramService(db)
        deployment = service.deploy_program(
            program_id=program_id,
            machine_id=request.machine_id,
            deployed_filename=request.deployed_filename,
            validate=request.validate_before_upload,
        )
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/machines/{machine_id}/deployments", response_model=List[ProgramDeploymentResponse])
async def list_machine_deployments(
    machine_id: int,
    current_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all program deployments for a machine.

    Shows full history of what programs were deployed when.
    current_only: Only show currently deployed programs (is_current=True)
    """
    query = db.query(ProgramDeployment).filter(ProgramDeployment.machine_id == machine_id)

    if current_only:
        query = query.filter(ProgramDeployment.is_current)

    query = query.order_by(ProgramDeployment.deployed_at.desc())
    deployments = query.offset(skip).limit(limit).all()

    return deployments


@router.get("/{program_id}/deployments", response_model=List[ProgramDeploymentResponse])
async def list_program_deployments(
    program_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all deployments of a specific program.

    Shows where this program has been deployed across all machines.
    """
    query = (
        db.query(ProgramDeployment)
        .filter(ProgramDeployment.program_id == program_id)
        .order_by(ProgramDeployment.deployed_at.desc())
    )

    deployments = query.offset(skip).limit(limit).all()
    return deployments


@router.get("/machines/{machine_id}/deployments/by-onumber/{onumber}")
async def get_deployment_by_onumber(
    machine_id: int,
    onumber: str,  # Accept "2000", "O2000", or "O2000.nc"
    include_program: bool = True,
    include_history: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get current deployment info for an O-number file with full program details.

    Accepts flexible O-number formats: "2000", "O2000", "O2000.nc" (case-insensitive).
    Returns deployment record with full program details and validation results.

    If include_history=true, also returns all previous deployments for this O-number.
    """
    onumber_match = re.search(r"(\d+)", onumber)
    if not onumber_match:
        raise HTTPException(status_code=400, detail="Invalid O-number format")

    onumber_int = int(onumber_match.group(1))
    onumber_padded = f"{onumber_int:04d}"
    deployed_filename_padded = f"O{onumber_padded}.nc"
    deployed_filename_unpadded = f"O{onumber_int}.nc"

    query = (
        db.query(ProgramDeployment)
        .filter(
            ProgramDeployment.machine_id == machine_id,
            or_(
                ProgramDeployment.deployed_filename.ilike(deployed_filename_padded),
                ProgramDeployment.deployed_filename.ilike(deployed_filename_unpadded),
            ),
            ProgramDeployment.is_current,
        )
        .order_by(ProgramDeployment.deployed_at.desc())
    )

    if include_program:
        query = query.options(joinedload(ProgramDeployment.program))

    deployment = query.first()

    if not deployment:
        return {"deployment": None, "program": None}

    resolved_deployed_path = deployment.deployed_path
    try:
        def _path_depth(p: str) -> int:
            return len([seg for seg in str(p or "").replace("\\", "/").split("/") if seg])

        current_depth = _path_depth(resolved_deployed_path)
        if current_depth <= 1:
            better_path_row = (
                db.query(ProgramDeployment.deployed_path)
                .filter(
                    ProgramDeployment.machine_id == machine_id,
                    ProgramDeployment.program_id == deployment.program_id,
                    ProgramDeployment.deployed_filename.ilike(deployment.deployed_filename),
                    ProgramDeployment.deployed_path.isnot(None),
                )
                .order_by(ProgramDeployment.deployed_at.desc())
                .all()
            )

            for row in better_path_row:
                candidate = row.deployed_path
                if _path_depth(candidate) > current_depth:
                    resolved_deployed_path = candidate
                    break
    except Exception:
        resolved_deployed_path = deployment.deployed_path

    response: dict[str, Any] = {
        "deployment": {
            "id": deployment.id,
            "deployed_filename": deployment.deployed_filename,
            "deployed_path": resolved_deployed_path,
            "deployed_at": deployment.deployed_at,
            "validation_passed": deployment.validation_passed,
            "validation_results": deployment.validation_results,
        }
    }

    if include_program and deployment.program:
        program = deployment.program
        response["program"] = {
            "id": program.id,
            "original_filename": program.original_filename,
            "version_number": program.version_number,
            "posted_date": program.posted_date,
            "estimated_runtime_seconds": program.estimated_runtime_seconds,
            "program_metadata": program.program_metadata,
            "file_size_bytes": program.file_size_bytes,
            "line_count": program.line_count,
        }

    if include_history:
        history = (
            db.query(ProgramDeployment)
            .filter(
                ProgramDeployment.machine_id == machine_id,
                or_(
                    ProgramDeployment.deployed_filename.ilike(deployed_filename_padded),
                    ProgramDeployment.deployed_filename.ilike(deployed_filename_unpadded),
                ),
            )
            .order_by(ProgramDeployment.deployed_at.desc())
            .all()
        )

        response["history"] = [
            {
                "id": h.id,
                "deployed_at": h.deployed_at,
                "validation_passed": h.validation_passed,
                "replaced_at": h.replaced_at,
                "is_current": h.is_current,
                "program_version": h.program.version_number if h.program else None,
                "original_filename": h.program.original_filename if h.program else None,
            }
            for h in history
        ]

    return response


@router.get("/deployments/{deployment_id}")
async def get_deployment_by_id(deployment_id: int, db: Session = Depends(get_db)):
    """Get full deployment details by deployment ID."""
    deployment = (
        db.query(ProgramDeployment)
        .options(joinedload(ProgramDeployment.program))
        .filter(ProgramDeployment.id == deployment_id)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

    response: dict[str, Any] = {
        "deployment": {
            "id": deployment.id,
            "deployed_filename": deployment.deployed_filename,
            "deployed_path": deployment.deployed_path,
            "deployed_at": deployment.deployed_at,
            "validation_passed": deployment.validation_passed,
            "validation_results": deployment.validation_results,
        }
    }

    if deployment.program:
        program = deployment.program
        response["program"] = {
            "id": program.id,
            "original_filename": program.original_filename,
            "version_number": program.version_number,
            "posted_date": program.posted_date,
            "estimated_runtime_seconds": program.estimated_runtime_seconds,
            "program_metadata": program.program_metadata,
            "file_size_bytes": program.file_size_bytes,
            "line_count": program.line_count,
        }

    return response


class ValidationPatchRequest(BaseModel):
    validation_results: dict[str, Any]
    validation_passed: bool


@router.patch("/deployments/{deployment_id}/validation")
async def update_deployment_validation(
    deployment_id: int,
    body: ValidationPatchRequest,
    db: Session = Depends(get_db),
):
    """Overwrite stored validation results for a deployment."""
    deployment = db.query(ProgramDeployment).filter(ProgramDeployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

    deployment.validation_results = body.validation_results
    deployment.validation_passed = body.validation_passed
    db.commit()

    return {"id": deployment_id, "validation_passed": deployment.validation_passed}


@router.get("/machines/{machine_id}/next-onumber")
async def get_next_onumber_fifo(
    machine_id: int,
    filename: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get next available O-number using FIFO allocation (O2000-O3999).
    """
    MIN_ONUMBER = 2000
    MAX_ONUMBER = 3999
    MAX_CAPACITY = 2000

    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    existing_deployment = None
    if filename:
        import urllib.parse

        filename_normalized = urllib.parse.unquote_plus(filename).strip()

        programs_with_filename = db.query(Program).filter(Program.original_filename == filename_normalized).all()

        if not programs_with_filename:
            programs_with_filename = (
                db.query(Program)
                .filter(func.lower(Program.original_filename) == func.lower(filename_normalized))
                .all()
            )

        for program in programs_with_filename:
            deployment = (
                db.query(ProgramDeployment)
                .filter(
                    ProgramDeployment.program_id == program.id,
                    ProgramDeployment.machine_id == machine_id,
                )
                .order_by(ProgramDeployment.id.desc())
                .first()
            )

            if deployment:
                if not existing_deployment or deployment.id > existing_deployment.id:
                    existing_deployment = deployment

        if existing_deployment:
            try:
                match = re.match(r"O(\d{4})", existing_deployment.deployed_filename, re.IGNORECASE)
                if match:
                    o_num = int(match.group(1))
                    return {
                        "next_onumber": f"O{o_num}.nc",
                        "onumber_int": o_num,
                        "is_replacing": False,
                        "replacement_info": None,
                        "is_redeployment": True,
                    }
            except Exception:
                existing_deployment = None

    deployments = (
        db.query(ProgramDeployment)
        .filter(
            ProgramDeployment.machine_id == machine_id,
            ProgramDeployment.is_current,
        )
        .order_by(ProgramDeployment.deployed_at.asc())
        .all()
    )

    existing: dict[int, ProgramDeployment] = {}
    for d in deployments:
        match = re.match(r"O(\d{4})", d.deployed_filename, re.IGNORECASE)
        if match:
            o_num = int(match.group(1))
            if MIN_ONUMBER <= o_num <= MAX_ONUMBER:
                existing[o_num] = d

    if len(existing) < MAX_CAPACITY:
        for o in range(MIN_ONUMBER, MAX_ONUMBER + 1):
            if o not in existing:
                return {
                    "next_onumber": f"O{o}.nc",
                    "onumber_int": o,
                    "is_replacing": False,
                    "replacement_info": None,
                    "is_redeployment": False,
                }

    oldest = deployments[0]
    match = re.match(r"O(\d{4})", oldest.deployed_filename, re.IGNORECASE)
    if match:
        o_num = int(match.group(1))
        if MIN_ONUMBER <= o_num <= MAX_ONUMBER:
            return {
                "next_onumber": f"O{o_num}.nc",
                "onumber_int": o_num,
                "is_replacing": True,
                "replacement_info": {
                    "onumber": str(o_num),
                    "deployed_at": oldest.deployed_at.isoformat(),
                    "original_filename": oldest.program.original_filename if oldest.program else "Unknown",
                },
                "is_redeployment": False,
            }

    return {
        "next_onumber": f"O{MIN_ONUMBER}.nc",
        "onumber_int": MIN_ONUMBER,
        "is_replacing": False,
        "replacement_info": None,
        "is_redeployment": False,
    }

