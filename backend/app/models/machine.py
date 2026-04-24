"""Machine model - stores CNC machine configurations."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Machine(Base):
    """CNC Machine configuration and metadata."""

    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    model = Column(String(100), default="Brother CNC")
    ip_address = Column(String(45), nullable=False)
    ftp_port = Column(Integer, default=21)
    http_port = Column(Integer, default=80)
    ftp_username = Column(String(255), default="anonymous")
    ftp_password = Column(String(255), default="anonymous")
    path = Column(String(255), default="/")
    tags = Column(JSON, nullable=True)  # ["production", "floor-a"]
    poll_interval_seconds = Column(Integer, default=5)
    tool_poll_interval_seconds = Column(Integer, default=30)  # Tool table/ATC polling interval (slower than fast poll)
    enabled = Column(Boolean, default=True)

    # Validation tolerances (in inches)
    diameter_tolerance = Column(Float, default=0.010)      # ±0.010" for diameter
    length_tolerance_plus = Column(Float, default=0.02)    # +0.02" for length
    length_tolerance_minus = Column(Float, default=0.0)    # -0mm
    tolerance_x = Column(Float, default=0.0394)            # ±1mm = ±0.0394 inches
    tolerance_y = Column(Float, default=0.0394)            # ±1mm = ±0.0394 inches
    tolerance_z = Column(Float, default=0.0394)            # ±1mm = ±0.0394 inches

    # Tolerance override flags
    use_machine_tool_tolerances = Column(Boolean, default=False)  # Use machine tolerances vs G-code defaults
    use_machine_wcs_tolerances = Column(Boolean, default=False)    # Use machine tolerances vs G-code E parameter
    validate_tool_diameter = Column(Boolean, default=True)          # Validate diameter in tool checks
    validate_tool_length = Column(Boolean, default=True)            # Validate length in tool checks

    # Measurement units
    units = Column(String(2), default='in')  # 'in' for inches, 'mm' for millimeters
    # Control platform version
    control_version = Column(String(3), nullable=True)  # 'C00', 'D00', or NULL for auto-detect

    # UI layout configuration (JSON)
    layout_config = Column(JSON, nullable=True)  # Custom pane layout configuration

    # UI preferences
    part_display_mode = Column(String(20), default="parts")  # 'parts' | 'cycle'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    program_deployments = relationship("ProgramDeployment", back_populates="machine", cascade="all, delete-orphan")
    ftp_sync_configs = relationship("FtpSyncConfig", back_populates="machine", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Machine(id={self.id}, name='{self.name}', ip='{self.ip_address}')>"
