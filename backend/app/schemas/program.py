"""Pydantic schemas for NC programs and deployments."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== Metadata Schemas ==========

class ToolOperationData(BaseModel):
    """Operation data for a single tool operation."""

    operation_name: Optional[str] = None
    spindle_speed: Optional[int] = None
    feedrate_cutting: Optional[float] = None
    feedrate_finish: Optional[float] = None
    feedrate_entry: Optional[float] = None
    feedrate_exit: Optional[float] = None
    feedrate_direct: Optional[float] = None
    feedrate_plunge: Optional[float] = None
    feedrate_transition: Optional[float] = None


class ToolMetadata(BaseModel):
    """Tool information extracted from G-code."""

    tool_number: int
    diameter: float
    corner_radius: float
    description: str
    length_total: float
    operations: Optional[List[ToolOperationData]] = None


class WCSOffsetMetadata(BaseModel):
    """WCS offset validation data extracted from G-code."""

    x: float
    y: float
    z: float
    work_offset: int  # 54 = G54, 55 = G55, etc.
    tolerance: float


class StockSizeMetadata(BaseModel):
    """Stock dimensions extracted from G-code."""

    x: float
    y: float
    z: float


# ========== Program Schemas ==========

class ProgramBase(BaseModel):
    """Base program schema."""

    original_filename: str
    content_hash: str
    posted_date: Optional[datetime] = None
    version_number: int
    program_metadata: Dict[str, Any] = {}
    file_size_bytes: int
    line_count: int
    estimated_runtime_seconds: Optional[float] = None


class ProgramCreate(BaseModel):
    """Schema for creating/uploading a new program."""

    gcode_content: str
    original_filename: str


class ProgramResponse(ProgramBase):
    """Program response with full details."""

    id: int
    first_seen_at: datetime
    last_deployed_at: Optional[datetime] = None
    deployed_count: int
    is_active: bool

    class Config:
        from_attributes = True


class ProgramListItem(BaseModel):
    """Simplified program info for list views."""

    id: int
    original_filename: str
    version_number: int
    posted_date: Optional[datetime] = None
    file_size_bytes: int
    estimated_runtime_seconds: Optional[float] = None
    first_seen_at: datetime
    deployed_count: int
    is_active: bool

    class Config:
        from_attributes = True


# ========== Deployment Schemas ==========

class ProgramDeploymentCreate(BaseModel):
    """Request to deploy a program to a machine."""

    program_id: int
    machine_id: int
    deployed_filename: str  # e.g., "O2000.nc"
    validate_before_upload: bool = True


class ProgramDeploymentResponse(BaseModel):
    """Deployment record response."""

    id: int
    program_id: int
    machine_id: int
    deployed_filename: str
    deployed_path: str
    deployed_at: datetime
    deployed_by: Optional[str] = None
    validation_results: Optional[Dict[str, Any]] = None
    validation_passed: bool
    is_current: bool
    replaced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Upload & Validation ==========

class ProgramUploadRequest(BaseModel):
    """Request to upload and optionally deploy a program."""

    gcode_content: str
    original_filename: str
    machine_id: Optional[int] = None  # If provided, deploy to this machine
    deployed_filename: Optional[str] = None  # O-number basename if deploying (e.g. "O0003.nc")
    deployed_path: Optional[str] = None  # Full remote path if known (e.g. "/FOLDER_A/O0003.nc")
    validate_before_upload: bool = True
    validation_results: Optional[Dict[str, Any]] = None  # Pre-computed validation results to store


class ProgramUploadResponse(BaseModel):
    """Response from program upload."""

    program: ProgramResponse
    is_new_version: bool  # True if new, False if already exists
    deployment: Optional[ProgramDeploymentResponse] = None  # If deployed
    validation_results: Optional[Dict[str, Any]] = None
