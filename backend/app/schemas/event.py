"""Pydantic schemas for event tracking."""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


# ========== Machine Status Events ==========

class MachineStatusEventCreate(BaseModel):
    """Create a status event."""

    machine_id: int
    status: str  # 'running', 'stopped', 'error', 'alarm', 'idle'
    previous_status: Optional[str] = None
    program_name: Optional[str] = None
    o_number: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class MachineStatusEventResponse(BaseModel):
    """Status event response."""

    time: datetime
    machine_id: int
    status: str
    previous_status: Optional[str] = None
    program_name: Optional[str] = None
    o_number: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CompressorStatusEventResponse(BaseModel):
    """Compressor status event response."""

    time: datetime
    compressor_id: int
    status: str
    previous_status: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CompressorStatusSampleResponse(BaseModel):
    """Single MQTT-throttled compressor status sample (time-ordered for oscilloscope)."""

    time: datetime
    compressor_id: int
    status: str
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ========== Alarm Events ==========

class AlarmEventCreate(BaseModel):
    """Create an alarm event."""

    machine_id: int
    alarm_code: str
    alarm_message: str
    alarm_type: Optional[str] = None
    severity: Optional[str] = None
    program_id: Optional[int] = None
    deployment_id: Optional[int] = None


class AlarmEventResponse(BaseModel):
    """Alarm event response."""

    time: datetime
    machine_id: int
    alarm_code: str
    alarm_message: str
    alarm_type: Optional[str] = None
    severity: Optional[str] = None
    program_id: Optional[int] = None
    deployment_id: Optional[int] = None
    cleared_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cleared_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    class Config:
        from_attributes = True


# ========== Production Runs ==========

class ProductionRunCreate(BaseModel):
    """Create a production run record."""

    machine_id: int
    program_id: Optional[int] = None
    deployment_id: Optional[int] = None
    program_name: Optional[str] = None
    o_number: Optional[str] = None
    started_at: datetime


class ProductionRunUpdate(BaseModel):
    """Update production run (when it ends)."""

    ended_at: Optional[datetime] = None
    cycle_count: Optional[int] = None
    parts_produced: Optional[int] = None
    completion_status: Optional[str] = None
    abort_reason: Optional[str] = None


class ProductionRunResponse(BaseModel):
    """Production run response."""

    id: int
    machine_id: int
    program_id: Optional[int] = None
    deployment_id: Optional[int] = None
    program_name: Optional[str] = None
    o_number: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    cycle_count: int
    parts_produced: int
    duration_seconds: Optional[int] = None
    actual_cycle_time_seconds: Optional[float] = None
    estimated_cycle_time_seconds: Optional[float] = None
    efficiency_percent: Optional[float] = None
    completion_status: Optional[str] = None
    abort_reason: Optional[str] = None
    alarm_count: int
    total_downtime_seconds: int

    class Config:
        from_attributes = True
