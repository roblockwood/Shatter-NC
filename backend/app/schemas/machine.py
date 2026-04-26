"""Pydantic schemas for Machine API endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class MachineBase(BaseModel):
    """Base schema for machine data."""

    name: str = Field(..., min_length=1, max_length=255)
    model: str = Field(default="Brother CNC", max_length=100)
    ip_address: str = Field(..., description="IPv4 or IPv6 address")
    ftp_port: int = Field(default=21, ge=1, le=65535)
    http_port: int = Field(default=80, ge=1, le=65535)
    ftp_username: str = Field(default="anonymous", max_length=255)
    ftp_password: str = Field(default="anonymous", max_length=255)
    path: str = Field(default="/", max_length=255, description="Default FTP path for program files (root)")
    tags: Optional[List[str]] = Field(default_factory=list)
    poll_interval_seconds: int = Field(default=5, ge=1, le=300)
    enabled: bool = Field(default=True)
    # Validation tolerances (in inches)
    diameter_tolerance: float = Field(default=0.010, ge=0, description="Tool diameter tolerance (±)")
    length_tolerance_plus: float = Field(default=0.02, ge=0, description="Tool length tolerance positive direction (+)")
    length_tolerance_minus: float = Field(default=0.0, ge=0, description="Tool length tolerance negative direction (-)")
    tolerance_x: float = Field(default=0.0394, ge=0, description="WCS X offset tolerance (±)")
    tolerance_y: float = Field(default=0.0394, ge=0, description="WCS Y offset tolerance (±)")
    tolerance_z: float = Field(default=0.0394, ge=0, description="WCS Z offset tolerance (±)")
    # Tolerance override flags
    use_machine_tool_tolerances: bool = Field(default=False, description="Use machine-defined tool tolerances instead of G-code defaults (exact match for diameter, length >= required)")
    use_machine_wcs_tolerances: bool = Field(default=False, description="Use machine-defined WCS tolerances instead of G-code E parameter")
    validate_tool_diameter: bool = Field(default=True, description="Whether to validate tool diameter")
    validate_tool_length: bool = Field(default=True, description="Whether to validate tool length")
    # Measurement units
    units: str = Field(default='in', description="Measurement units: 'in' for inches, 'mm' for millimeters")
    control_version: Optional[Literal['C00', 'D00']] = Field(default=None, description="Control version override. Set to C00 or D00 to disable auto-detection")
    layout_config: Optional[Dict[str, Any]] = Field(default=None, description="Custom pane layout configuration")
    part_display_mode: str = Field(default="parts", description="Compact machine card count label: 'parts' or 'cycle'")


class MachineCreate(MachineBase):
    """Schema for creating a new machine."""

    pass


class MachineUpdate(BaseModel):
    """Schema for updating a machine (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    model: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = None
    ftp_port: Optional[int] = Field(None, ge=1, le=65535)
    http_port: Optional[int] = Field(None, ge=1, le=65535)
    ftp_username: Optional[str] = Field(None, max_length=255)
    ftp_password: Optional[str] = Field(None, max_length=255)
    path: Optional[str] = Field(None, max_length=255, description="Default FTP path for program files")
    tags: Optional[List[str]] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=1, le=300)
    enabled: Optional[bool] = None
    # Validation tolerances (in inches)
    diameter_tolerance: Optional[float] = Field(None, ge=0, description="Tool diameter tolerance (±)")
    length_tolerance_plus: Optional[float] = Field(None, ge=0, description="Tool length tolerance positive direction (+)")
    length_tolerance_minus: Optional[float] = Field(None, ge=0, description="Tool length tolerance negative direction (-)")
    tolerance_x: Optional[float] = Field(None, ge=0, description="WCS X offset tolerance (±)")
    tolerance_y: Optional[float] = Field(None, ge=0, description="WCS Y offset tolerance (±)")
    tolerance_z: Optional[float] = Field(None, ge=0, description="WCS Z offset tolerance (±)")
    # Tolerance override flags
    use_machine_tool_tolerances: Optional[bool] = Field(None, description="Use machine-defined tool tolerances instead of G-code defaults (exact match for diameter, length >= required)")
    use_machine_wcs_tolerances: Optional[bool] = Field(None, description="Use machine-defined WCS tolerances instead of G-code E parameter")
    validate_tool_diameter: Optional[bool] = Field(None, description="Whether to validate tool diameter")
    validate_tool_length: Optional[bool] = Field(None, description="Whether to validate tool length")
    # Measurement units
    units: Optional[str] = Field(None, description="Measurement units: 'in' for inches, 'mm' for millimeters")
    control_version: Optional[Literal['C00', 'D00']] = Field(None, description="Control version override. Set to C00 or D00 to disable auto-detection")
    layout_config: Optional[Dict[str, Any]] = Field(None, description="Custom pane layout configuration")
    part_display_mode: Optional[str] = Field(None, description="Compact machine card count label: 'parts' or 'cycle'")


class MachineResponse(MachineBase):
    """Schema for machine responses."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MachineStatus(BaseModel):
    """Real-time machine status."""

    machine_id: int
    status: str  # running, stopped, error, alarm
    program_name: Optional[str] = None
    cycle_time_seconds: Optional[int] = None
    cutting_time_seconds: Optional[int] = None
    power_on_hours: Optional[float] = None
    response_time_ms: Optional[int] = None
    tool_response_time_ms: Optional[int] = None
    timestamp: datetime
