"""Program validation, upload, and deployment endpoints.

Routes are split across focused sub-modules:
  _programs_validate.py  — POST validate, POST validate-file + helpers
  _programs_library.py   — GET/POST program library (list, get, upload, deploy-validated)
  _programs_deploy.py    — deployment management + FIFO O-number allocation
  _programs_atc.py       — POST analyze-atc (ATC pot optimizer)

All 14 routes and all public import paths are preserved unchanged.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.program import Program
from app.schemas.program import ProgramListItem
import app.api._programs_validate as _validate
import app.api._programs_library as _library
import app.api._programs_deploy as _deploy
import app.api._programs_atc as _atc

# Re-export models so existing callers can still do:
#   from app.api.programs import ProgramValidationResponse
from app.api._programs_validate import (  # noqa: F401
    ProgramValidateRequest,
    ToolValidationResult,
    WCSValidationResult,
    ProgramValidationResponse,
    ProgramValidationWithContentResponse,
    DeployValidatedRequest,
    _validate_tool,
    _validate_wcs_offset,
    validate_program,
)
from app.api._programs_library import (  # noqa: F401
    upload_program,
)
from app.api._programs_atc import (  # noqa: F401
    ATCOptimizeRequest,
    ATCAssignmentEntry,
    ATCOptimizeResponse,
)

router = APIRouter()
router.include_router(_validate.router)
router.include_router(_library.router)
router.include_router(_deploy.router)
router.include_router(_atc.router)


@router.get("", response_model=List[ProgramListItem])
async def list_programs(
    skip: int = 0,
    limit: int = 100,
    filename_filter: str = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    List all programs in the library.

    Query params:
    - filename_filter: Filter by filename (partial match)
    - active_only: Only show active versions (default: True)
    """
    query = db.query(Program)

    if active_only:
        query = query.filter(Program.is_active)

    if filename_filter:
        query = query.filter(Program.original_filename.ilike(f"%{filename_filter}%"))

    query = query.order_by(Program.first_seen_at.desc())
    programs = query.offset(skip).limit(limit).all()

    return programs
