"""Program and deployment models for NC file version tracking."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import hashlib


class Program(Base):
    """NC Program with automatic version tracking per filename."""

    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)

    # Program identity (filename-based)
    original_filename = Column(String(500), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Versioning
    posted_date = Column(DateTime(timezone=True), index=True)
    version_number = Column(Integer, nullable=False)

    # Parsed metadata (JSONB for flexibility)
    program_metadata = Column(JSONB, nullable=False, server_default='{}')
    # Structure: {
    #   "tools": [{"tool_number": 1, "diameter": 0.25, "corner_radius": 0, ...}],
    #   "wcs_offset": {"x": -21.99, "y": -2.85, "z": -15.89, "work_offset": 54, "tolerance": 2.0},
    #   "stock_size": {"x": 146.05, "y": 25.4, "z": 12.7}
    # }

    # File characteristics
    file_size_bytes = Column(Integer, nullable=False)
    line_count = Column(Integer, nullable=False)
    estimated_runtime_seconds = Column(Float)

    # Audit
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_deployed_at = Column(DateTime(timezone=True))
    deployed_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    deployments = relationship("ProgramDeployment", back_populates="program", cascade="all, delete-orphan")
    production_runs = relationship("ProductionRun", back_populates="program", cascade="all, delete-orphan")
    alarm_events = relationship("AlarmEvent", back_populates="program", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('version_number > 0', name='positive_version'),
    )

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of program content."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def __repr__(self):
        return f"<Program(id={self.id}, filename='{self.original_filename}', v{self.version_number}, hash={self.content_hash[:8]}...)>"


class ProgramDeployment(Base):
    """Tracks deployment of a program to a specific machine with O-number mapping."""

    __tablename__ = "program_deployments"

    id = Column(Integer, primary_key=True, index=True)

    # References
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)

    # Deployment details
    deployed_filename = Column(String(500), nullable=False)  # "O2000.nc"
    deployed_path = Column(String(500), nullable=False)      # "/PROGRAM/O2000.nc"

    # Timing
    deployed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    deployed_by = Column(String(255))  # Future: user tracking

    # Validation results (captured at deploy time)
    validation_results = Column(JSONB)
    validation_passed = Column(Boolean, default=True)

    # O-number reuse tracking
    is_current = Column(Boolean, default=True, index=True)
    replaced_at = Column(DateTime(timezone=True))
    replaced_by = Column(Integer, ForeignKey("program_deployments.id", ondelete="SET NULL"))

    # Relationships
    program = relationship("Program", back_populates="deployments")
    machine = relationship("Machine", back_populates="program_deployments")
    production_runs = relationship("ProductionRun", back_populates="deployment", cascade="all, delete-orphan")
    alarm_events = relationship("AlarmEvent", back_populates="deployment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProgramDeployment(id={self.id}, program_id={self.program_id}, machine_id={self.machine_id}, {self.deployed_filename})>"
