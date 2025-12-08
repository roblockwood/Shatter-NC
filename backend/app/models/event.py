"""Event tracking models for TimescaleDB hypertables."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class MachineStatusEvent(Base):
    """Machine status change events (TimescaleDB hypertable)."""

    __tablename__ = "machine_status_events"

    # TimescaleDB time column (must be part of primary key)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)

    # Status
    status = Column(String(50), nullable=False, index=True)
    previous_status = Column(String(50))

    # Context
    program_name = Column(String(500))
    o_number = Column(String(50))

    # Metrics (JSONB for flexibility)
    metrics = Column(JSONB)
    # Structure: {
    #   "cycle_time_seconds": 1234,
    #   "cutting_time_seconds": 890,
    #   "power_on_hours": 12345.6
    # }

    # Relationships
    machine = relationship("Machine")

    def __repr__(self):
        return f"<MachineStatusEvent(machine_id={self.machine_id}, status='{self.status}', time={self.time})>"


class AlarmEvent(Base):
    """Alarm occurrence tracking (TimescaleDB hypertable)."""

    __tablename__ = "alarm_events"

    # Primary key (TimescaleDB composite with time and machine_id)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)
    alarm_code = Column(String(50), primary_key=True, nullable=False, index=True)

    # Alarm details
    alarm_message = Column(Text, nullable=False)
    alarm_type = Column(String(50))
    severity = Column(String(20))

    # Context
    program_id = Column(Integer, ForeignKey("programs.id"), index=True)
    deployment_id = Column(Integer, ForeignKey("program_deployments.id"), index=True)

    # Duration tracking
    cleared_at = Column(DateTime(timezone=True), index=True)
    duration_seconds = Column(Integer)

    # Resolution
    cleared_by = Column(String(255))
    resolution_notes = Column(Text)

    # Relationships
    machine = relationship("Machine")
    program = relationship("Program", back_populates="alarm_events")
    deployment = relationship("ProgramDeployment", back_populates="alarm_events")

    def __repr__(self):
        return f"<AlarmEvent(machine_id={self.machine_id}, code='{self.alarm_code}', time={self.time})>"


class ProductionRun(Base):
    """Production run tracking (TimescaleDB hypertable)."""

    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True)

    # Time tracking (for TimescaleDB)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), index=True)

    # References
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), index=True)
    deployment_id = Column(Integer, ForeignKey("program_deployments.id"), index=True)

    # Program identification
    program_name = Column(String(500))
    o_number = Column(String(50))

    # Production metrics
    cycle_count = Column(Integer, default=0)
    parts_produced = Column(Integer, default=0)
    duration_seconds = Column(Integer)

    # Performance
    actual_cycle_time_seconds = Column(Float)
    estimated_cycle_time_seconds = Column(Float)
    efficiency_percent = Column(Float)

    # Status
    completion_status = Column(String(50), index=True)
    abort_reason = Column(String(500))

    # Alarms
    alarm_count = Column(Integer, default=0)
    total_downtime_seconds = Column(Integer, default=0)

    # Relationships
    machine = relationship("Machine")
    program = relationship("Program", back_populates="production_runs")
    deployment = relationship("ProgramDeployment", back_populates="production_runs")

    __table_args__ = (
        CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='valid_time_range'),
    )

    def __repr__(self):
        return f"<ProductionRun(id={self.id}, machine_id={self.machine_id}, program='{self.program_name}')>"


class PollingEvent(Base):
    """HTTP polling attempt tracking (TimescaleDB hypertable)."""

    __tablename__ = "polling_events"

    # TimescaleDB time column (must be part of primary key)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)

    # Poll result
    success = Column(Boolean, nullable=False, index=True)
    response_time_ms = Column(Integer)  # Milliseconds
    error_message = Column(String(500))

    # Relationships
    machine = relationship("Machine")

    def __repr__(self):
        return f"<PollingEvent(machine_id={self.machine_id}, time={self.time}, success={self.success})>"
