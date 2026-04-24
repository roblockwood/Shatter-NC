"""Pydantic schemas for FTP sync config and run endpoints."""
from datetime import datetime
from typing import Any, Optional
from typing import Literal

from pydantic import BaseModel, Field


class FtpSyncConfigBase(BaseModel):
    """Common sync configuration fields."""

    name: str = Field(..., min_length=1, max_length=255)
    sync_direction: Literal["upload", "download"] = Field(
        default="upload",
        description="upload = local->CNC, download = CNC->local",
    )
    source_folder: str = Field(..., min_length=1, max_length=1024)
    remote_folder: str = Field(default="/", min_length=1, max_length=1024)
    include_pattern: str = Field(default="*.NC", min_length=1, max_length=255)
    exclude_patterns: str = Field(
        default=".*,~*,*.tmp,*.temp,*.bak,*.swp,*.DS_Store",
        min_length=0,
        max_length=1024,
        description="Comma-separated glob patterns to exclude from sync",
    )
    control_type: Literal["C00", "D00"] = Field(default="C00", description="Brother control profile: C00 or D00")
    strict_brother_naming: bool = Field(default=True, description="Enforce Brother naming character and length limits")
    require_onumber_filename: bool = Field(default=True, description="Require O####.NC filenames")
    enabled: bool = True
    auto_validate: bool = True
    auto_register: bool = True
    debounce_seconds: int = Field(default=3, ge=0, le=120)


class FtpSyncConfigCreate(FtpSyncConfigBase):
    """Create payload for machine sync configuration."""


class FtpSyncConfigUpdate(BaseModel):
    """Patch payload for machine sync configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sync_direction: Optional[Literal["upload", "download"]] = None
    source_folder: Optional[str] = Field(None, min_length=1, max_length=1024)
    remote_folder: Optional[str] = Field(None, min_length=1, max_length=1024)
    include_pattern: Optional[str] = Field(None, min_length=1, max_length=255)
    exclude_patterns: Optional[str] = Field(None, min_length=0, max_length=1024)
    control_type: Optional[Literal["C00", "D00"]] = None
    strict_brother_naming: Optional[bool] = None
    require_onumber_filename: Optional[bool] = None
    enabled: Optional[bool] = None
    auto_validate: Optional[bool] = None
    auto_register: Optional[bool] = None
    debounce_seconds: Optional[int] = Field(None, ge=0, le=120)


class FtpSyncConfigResponse(FtpSyncConfigBase):
    """Sync configuration response payload."""

    id: int
    machine_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FtpSyncRunItemResponse(BaseModel):
    """Per-file result in a sync run."""

    id: int
    relative_path: str
    local_path: str
    remote_path: str
    content_hash: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    details: dict[str, Any] = {}

    class Config:
        from_attributes = True


class FtpSyncRunResponse(BaseModel):
    """Sync run status response."""

    id: int
    config_id: int
    machine_id: int
    trigger_source: str
    status: str
    total_files: int
    success_files: int
    failed_files: int
    conflict_files: int
    skipped_files: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FtpSyncRunDetailResponse(FtpSyncRunResponse):
    """Sync run with per-file entries."""

    items: list[FtpSyncRunItemResponse]


class FtpSyncTriggerRequest(BaseModel):
    """Manual run trigger payload."""

    relative_paths: Optional[list[str]] = None


class FtpSyncTriggerResponse(BaseModel):
    """Result after enqueuing a manual sync run."""

    run_id: int
    config_id: int
    status: str


class LocalFolderEntry(BaseModel):
    """One local filesystem directory entry for source-folder browsing."""

    name: str
    path: str


class LocalFolderBrowseResponse(BaseModel):
    """Directory listing response for local source-folder picker."""

    current_path: str
    parent_path: Optional[str] = None
    directories: list[LocalFolderEntry]
