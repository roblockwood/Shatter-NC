"""Program library routes — CRUD and upload.

Routes:
    GET  ""                                              — list programs
    GET  /{program_id}                                   — get program by ID
    GET  /by-filename/{filename}                         — get program versions by filename
    POST /upload                                         — upload a new NC program
    POST /machines/{machine_id}/programs/deploy-validated — record deployment of on-machine file
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

logger = logging.getLogger(__name__)

from app.db.base import get_db
from app.models.program import Program
from app.schemas.program import (
    ProgramUploadRequest,
    ProgramUploadResponse,
    ProgramResponse,
    ProgramDeploymentCreate,
    ProgramDeploymentResponse,
)
from app.services.program_service import ProgramService
from app.api._programs_validate import (
    ProgramValidateRequest,
    DeployValidatedRequest,
    validate_program,
)


router = APIRouter()


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: int, db: Session = Depends(get_db)):
    """Get detailed program information."""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.get("/by-filename/{filename}", response_model=List[ProgramResponse])
async def get_program_versions(filename: str, db: Session = Depends(get_db)):
    """Get all versions of a program by filename, ordered by version number (newest first)."""
    programs = db.query(Program).filter(
        Program.original_filename == filename
    ).order_by(Program.version_number.desc()).all()

    if not programs:
        raise HTTPException(status_code=404, detail="No programs found with that filename")

    return programs


@router.post("/upload", response_model=ProgramUploadResponse)
async def upload_program(
    request: ProgramUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Upload a new NC program.

    Flow:
    1. Parse G-code and extract metadata
    2. Compute content hash
    3. Check if program already exists (by hash)
    4. If new: create Program record with next version number
    5. If deploying: create deployment record with validation
    """
    try:
        service = ProgramService(db)

        validation_results = request.validation_results
        if request.validate_before_upload and request.machine_id and not validation_results:
            validate_request = ProgramValidateRequest(gcode_content=request.gcode_content)
            validation_results = await validate_program(
                machine_id=request.machine_id,
                request=validate_request,
                db=db
            )

        result = service.upload_program(
            gcode_content=request.gcode_content,
            original_filename=request.original_filename,
            machine_id=request.machine_id,
            deployed_filename=request.deployed_filename,
            deployed_path=request.deployed_path,
            validate=request.validate_before_upload,
            validation_results=validation_results
        )

        return ProgramUploadResponse(
            program=result["program"],
            is_new_version=result["is_new_version"],
            deployment=result["deployment"],
            validation_results=result["validation_results"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/machines/{machine_id}/programs/deploy-validated")
async def deploy_validated_program(
    machine_id: int,
    request: DeployValidatedRequest,
    db: Session = Depends(get_db)
):
    """
    Create a deployment record for a file already on the machine.

    The file is ALREADY on the machine - we're just creating a database record
    with validation results. This is different from upload which does FTP transfer.
    """
    try:
        service = ProgramService(db)

        result = service.upload_program(
            gcode_content=request.gcode_content,
            original_filename=request.deployed_filename,
            machine_id=machine_id,
            deployed_filename=request.deployed_filename,
            validate=False,
            validation_results=request.validation_results
        )

        return result["deployment"]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")
