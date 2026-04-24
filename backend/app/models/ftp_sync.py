"""FTP sync models for local-folder-to-machine upload workflows."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class FtpSyncConfig(Base):
    """Configuration for syncing a local folder to a machine over FTP."""

    __tablename__ = "ftp_sync_configs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sync_direction = Column(String(16), nullable=False, default="upload")
    source_folder = Column(String(1024), nullable=False)
    remote_folder = Column(String(1024), nullable=False, default="/")
    include_pattern = Column(String(255), nullable=False, default="*.NC")
    exclude_patterns = Column(String(1024), nullable=False, default=".*,~*,*.tmp,*.temp,*.bak,*.swp,*.DS_Store")
    control_type = Column(String(8), nullable=False, default="C00")
    strict_brother_naming = Column(Boolean, nullable=False, default=True)
    require_onumber_filename = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, nullable=False, default=True)
    auto_validate = Column(Boolean, nullable=False, default=True)
    auto_register = Column(Boolean, nullable=False, default=True)
    debounce_seconds = Column(Integer, nullable=False, default=3)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    machine = relationship("Machine", back_populates="ftp_sync_configs")
    runs = relationship("FtpSyncRun", back_populates="config", cascade="all, delete-orphan")
    file_states = relationship("FtpSyncFileState", back_populates="config", cascade="all, delete-orphan")


class FtpSyncRun(Base):
    """A sync run triggered manually or by local file-change detection."""

    __tablename__ = "ftp_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("ftp_sync_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_source = Column(String(50), nullable=False, default="manual")
    status = Column(String(32), nullable=False, default="queued", index=True)
    total_files = Column(Integer, nullable=False, default=0)
    success_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)
    conflict_files = Column(Integer, nullable=False, default=0)
    skipped_files = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    config = relationship("FtpSyncConfig", back_populates="runs")
    machine = relationship("Machine")
    items = relationship("FtpSyncRunItem", back_populates="run", cascade="all, delete-orphan")


class FtpSyncRunItem(Base):
    """Per-file outcome for a sync run."""

    __tablename__ = "ftp_sync_run_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("ftp_sync_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path = Column(String(1024), nullable=False)
    local_path = Column(String(2048), nullable=False)
    remote_path = Column(String(1024), nullable=False)
    content_hash = Column(String(64))
    status = Column(String(32), nullable=False, default="queued", index=True)
    error_message = Column(Text)
    details = Column(JSONB, nullable=False, server_default='{}')

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    run = relationship("FtpSyncRun", back_populates="items")


class FtpSyncFileState(Base):
    """Last known synced hash for a config-relative file path."""

    __tablename__ = "ftp_sync_file_states"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("ftp_sync_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path = Column(String(1024), nullable=False)
    last_uploaded_hash = Column(String(64), nullable=False)
    last_uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_uploaded_remote_path = Column(String(1024), nullable=False)

    config = relationship("FtpSyncConfig", back_populates="file_states")

    __table_args__ = (
        UniqueConstraint("config_id", "relative_path", name="uq_ftp_sync_file_state_config_path"),
    )
