"""Pydantic schemas for Machine API endpoints."""
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List
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
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(default_factory=list)
    poll_interval_seconds: int = Field(default=5, ge=1, le=300)
    enabled: bool = Field(default=True)


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
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=1, le=300)
    enabled: Optional[bool] = None


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
    timestamp: datetime
