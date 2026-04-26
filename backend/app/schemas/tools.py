"""Pydantic schemas for Tool Management API endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== OPERATION STATISTICS ====================

class OperationStats(BaseModel):
    """Speed/feed data for a specific operation within a program."""

    operation_name: Optional[str] = None
    spindle_speed: Optional[float] = Field(
        default=None,
        description="Spindle speed in RPM"
    )
    feedrate_cutting: Optional[float] = Field(
        default=None,
        description="Cutting feedrate in IPM"
    )
    feedrate_plunge: Optional[float] = Field(
        default=None,
        description="Plunge feedrate in IPM"
    )
    feedrate_finish: Optional[float] = Field(
        default=None,
        description="Finish feedrate in IPM"
    )
    feedrate_entry: Optional[float] = Field(
        default=None,
        description="Entry feedrate in IPM"
    )
    feedrate_exit: Optional[float] = Field(
        default=None,
        description="Exit feedrate in IPM"
    )
    feedrate_direct: Optional[float] = Field(
        default=None,
        description="Direct/rapid feedrate in IPM"
    )
    feedrate_transition: Optional[float] = Field(
        default=None,
        description="Transition feedrate in IPM"
    )


# ==================== TOOL SUMMARY ====================

class ToolSummary(BaseModel):
    """Summary information for a tool across all programs."""

    tool_number: int = Field(..., ge=1, description="Tool number")
    diameter: float = Field(..., description="Tool diameter in inches")
    description: str = Field(..., description="Tool type description")
    programs_using: int = Field(..., ge=0, description="Number of programs using this tool")
    estimated_runtime_seconds: float = Field(
        ...,
        ge=0,
        description="Estimated total runtime (program duration / tool count)"
    )
    total_runs: int = Field(..., ge=0, description="Total production runs using this tool")
    machines_used: List[int] = Field(default_factory=list, description="List of machine IDs that have used this tool")
    operation_types: List[str] = Field(
        default_factory=list,
        description="List of operation types this tool is used for"
    )


class ToolSummaryResponse(BaseModel):
    """Response for GET /api/tools/summary endpoint."""

    total_unique_tools: int = Field(..., ge=0, description="Total number of unique tools")
    total_programs: int = Field(..., ge=0, description="Total number of programs with tools")
    total_production_runs: int = Field(..., ge=0, description="Total production runs across all programs")
    tools: List[ToolSummary] = Field(default_factory=list, description="List of all tools")


# ==================== TOOL DETAIL ====================

class MachineUsage(BaseModel):
    """Machine-specific usage statistics for a tool."""

    machine_id: int
    machine_name: str
    production_runs: int = Field(..., ge=0, description="Number of production runs on this machine")
    runtime_seconds: float = Field(..., ge=0, description="Estimated runtime on this machine")


class ProgramUsage(BaseModel):
    """Program-specific usage information for a tool."""

    program_id: int
    filename: str
    deployed_path: Optional[str] = Field(default=None, description="Current deployed path (e.g. /PROGRAM/FOLDER/O0001.NC)")
    version: int
    production_runs: int = Field(..., ge=0, description="Number of production runs for this program")
    last_run: Optional[datetime] = Field(default=None, description="Timestamp of last production run")
    operations: List['OperationStats'] = Field(
        default_factory=list,
        description="Operations in this specific program with their speed/feed data"
    )


class AlarmSummary(BaseModel):
    """Alarm correlation summary for a tool."""

    alarm_code: str
    alarm_message: str
    occurrences: int = Field(..., ge=0, description="Number of times this alarm occurred")
    last_occurrence: Optional[datetime] = Field(default=None, description="Timestamp of last occurrence")


class ToolDetail(BaseModel):
    """Detailed analysis for a specific tool."""

    tool_number: int = Field(..., ge=1)
    specifications: Dict[str, Any] = Field(
        ...,
        description="Tool specifications: diameter_range, descriptions, length_range"
    )
    usage_statistics: Dict[str, Any] = Field(
        ...,
        description="Usage stats: total_programs, total_production_runs, estimated_runtime_seconds, total_parts_produced"
    )
    machines: List[MachineUsage] = Field(
        default_factory=list,
        description="Per-machine usage breakdown"
    )
    programs: List[ProgramUsage] = Field(
        default_factory=list,
        description="List of programs using this tool with their operations"
    )
    alarms: List[AlarmSummary] = Field(
        default_factory=list,
        description="Alarms correlated with this tool"
    )


# ==================== PRODUCTION RUN HISTORY ====================

class ProductionRunSummary(BaseModel):
    """Summary of a production run for tool history."""

    run_id: int
    machine_id: int
    machine_name: str
    program_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    parts_produced: int = Field(..., ge=0)
    alarm_count: int = Field(..., ge=0)
    completion_status: Optional[str] = None


class ToolHistoryResponse(BaseModel):
    """Response for GET /api/tools/{tool_number}/history endpoint."""

    tool_number: int
    total_runs: int = Field(..., ge=0, description="Total number of runs in filtered results")
    runs: List[ProductionRunSummary] = Field(default_factory=list, description="List of production runs")


# ==================== EXPORT ====================

class ExportFilters(BaseModel):
    """Filters for data export."""

    tool_numbers: Optional[List[int]] = Field(
        default=None,
        description="Filter by specific tool numbers"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter production runs after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter production runs before this date"
    )
    machine_ids: Optional[List[int]] = Field(
        default=None,
        description="Filter by specific machine IDs"
    )


class ExportRequest(BaseModel):
    """Request schema for POST /api/tools/export endpoint."""

    format: str = Field(
        ...,
        pattern="^(csv|json)$",
        description="Export format: 'csv' or 'json'"
    )
    filters: Optional[ExportFilters] = Field(
        default_factory=ExportFilters,
        description="Optional filters for export data"
    )
    include_operations: bool = Field(
        default=True,
        description="Include operation-level speed/feed data"
    )
    include_programs: bool = Field(
        default=False,
        description="Include program usage details"
    )


# ==================== TOOL INSTANCE (FUTURE) ====================

class ToolInstanceBase(BaseModel):
    """Base schema for tool instance data."""

    tool_number: int = Field(..., ge=1)
    diameter: float
    corner_radius: float = 0.0
    description: Optional[str] = None
    length_total: Optional[float] = None
    removal_reason: Optional[str] = Field(
        default=None,
        description="Reason for removal: 'normal_wear', 'breakage', 'upgrade', 'scheduled'"
    )
    notes: Optional[str] = None


class ToolInstanceCreate(ToolInstanceBase):
    """Schema for creating a new tool instance."""

    machine_id: int


class ToolInstanceResponse(ToolInstanceBase):
    """Schema for tool instance responses."""

    id: int
    machine_id: int
    installed_at: datetime
    removed_at: Optional[datetime] = None
    total_runtime_seconds: int = 0
    total_parts_produced: int = 0
    total_cycles: int = 0
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class ToolInstancesResponse(BaseModel):
    """Response for GET /api/tools/instances/{machine_id} endpoint."""

    machine_id: int
    total_instances: int = Field(..., ge=0, description="Total number of tool instances")
    active_instances: int = Field(..., ge=0, description="Currently active tool instances")
    instances: List[ToolInstanceResponse] = Field(
        default_factory=list,
        description="List of tool instances"
    )
    note: str = Field(
        default="Tool instance tracking is currently unpopulated. This is infrastructure for future tool replacement tracking.",
        description="Informational note about tool instance status"
    )
