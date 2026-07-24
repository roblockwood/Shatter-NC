"""API endpoints for FTP folder sync configuration and run status."""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.models.ftp_sync import FtpSyncConfig, FtpSyncRun, FtpSyncRunItem
from app.models.machine import Machine
from app.schemas.ftp_sync import (
    FtpSyncConfigCreate,
    FtpSyncConfigResponse,
    FtpSyncConfigUpdate,
    LocalFolderBrowseResponse,
    LocalFolderEntry,
    FtpSyncRunDetailResponse,
    FtpSyncRunResponse,
    FtpSyncTriggerRequest,
    FtpSyncTriggerResponse,
)

router = APIRouter()

ftp_sync_service = None


def set_ftp_sync_service(service):
    """Inject singleton FTP sync service from main app."""
    global ftp_sync_service
    ftp_sync_service = service


def _require_ftp_sync_enabled(machine: Machine) -> None:
    if not machine.ftp_sync_enabled:
        raise HTTPException(status_code=403, detail="FTP sync is not enabled for this machine")


def _resolve_local_browse_path(path: Optional[str] = None) -> Path:
    """Resolve and validate requested browse path under configured root."""
    browse_root = Path(settings.FTP_SYNC_LOCAL_BROWSE_ROOT).expanduser().resolve()

    if not path:
        requested = browse_root
    else:
        requested = Path(path).expanduser().resolve()
        # Allow shorthand paths like "/blackwellengineering" by interpreting them
        # as children under the configured browse root.
        if requested != browse_root:
            try:
                requested.relative_to(browse_root)
            except ValueError:
                requested = (browse_root / path.lstrip("/")).resolve()

    if not requested.exists() or not requested.is_dir():
        raise HTTPException(status_code=404, detail="Local folder does not exist")

    try:
        requested.relative_to(browse_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Requested path is outside allowed browse root") from exc

    return requested


@router.get(
    "/machines/{machine_id}/ftp-sync/local-folders",
    response_model=LocalFolderBrowseResponse,
)
async def browse_local_folders(
    machine_id: int,
    path: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Browse local directories for selecting sync source_folder."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    current = _resolve_local_browse_path(path)
    browse_root = Path(settings.FTP_SYNC_LOCAL_BROWSE_ROOT).expanduser().resolve()

    directories: List[LocalFolderEntry] = []
    for child in sorted(current.iterdir(), key=lambda p: p.name.lower()):
        # Skip hidden entries first to avoid stat'ing paths like .Trash that may
        # raise PermissionError in containerized host mounts.
        if child.name.startswith('.'):
            continue
        try:
            if not child.is_dir():
                continue
            directories.append(LocalFolderEntry(name=child.name, path=str(child.resolve())))
        except (PermissionError, OSError):
            # Ignore unreadable/unstatable entries and continue listing the rest.
            continue

    parent_path = None
    if current != browse_root:
        parent = current.parent.resolve()
        try:
            parent.relative_to(browse_root)
            parent_path = str(parent)
        except ValueError:
            parent_path = str(browse_root)

    return LocalFolderBrowseResponse(
        current_path=str(current),
        parent_path=parent_path,
        directories=directories,
    )


@router.get("/machines/{machine_id}/ftp-sync/configs", response_model=list[FtpSyncConfigResponse])
async def list_sync_configs(machine_id: int, db: Session = Depends(get_db)):
    """List FTP sync configurations for one machine."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    return (
        db.query(FtpSyncConfig)
        .filter(FtpSyncConfig.machine_id == machine_id)
        .order_by(FtpSyncConfig.id.asc())
        .all()
    )


@router.post(
    "/machines/{machine_id}/ftp-sync/configs",
    response_model=FtpSyncConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sync_config(
    machine_id: int,
    payload: FtpSyncConfigCreate,
    db: Session = Depends(get_db),
):
    """Create FTP sync configuration for one machine."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    _require_ftp_sync_enabled(machine)

    config = FtpSyncConfig(machine_id=machine_id, **payload.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/machines/{machine_id}/ftp-sync/configs/{config_id}", response_model=FtpSyncConfigResponse)
async def update_sync_config(
    machine_id: int,
    config_id: int,
    payload: FtpSyncConfigUpdate,
    db: Session = Depends(get_db),
):
    """Update FTP sync configuration."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    _require_ftp_sync_enabled(machine)

    config = (
        db.query(FtpSyncConfig)
        .filter(FtpSyncConfig.id == config_id, FtpSyncConfig.machine_id == machine_id)
        .first()
    )
    if not config:
        raise HTTPException(status_code=404, detail="Sync config not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


@router.delete("/machines/{machine_id}/ftp-sync/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sync_config(machine_id: int, config_id: int, db: Session = Depends(get_db)):
    """Delete FTP sync configuration."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    _require_ftp_sync_enabled(machine)

    config = (
        db.query(FtpSyncConfig)
        .filter(FtpSyncConfig.id == config_id, FtpSyncConfig.machine_id == machine_id)
        .first()
    )
    if not config:
        raise HTTPException(status_code=404, detail="Sync config not found")

    db.delete(config)
    db.commit()
    return None


@router.post(
    "/machines/{machine_id}/ftp-sync/configs/{config_id}/trigger",
    response_model=FtpSyncTriggerResponse,
)
async def trigger_sync_run(
    machine_id: int,
    config_id: int,
    payload: FtpSyncTriggerRequest,
    db: Session = Depends(get_db),
):
    """Trigger a manual sync run for one configuration."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    _require_ftp_sync_enabled(machine)

    config = (
        db.query(FtpSyncConfig)
        .filter(FtpSyncConfig.id == config_id, FtpSyncConfig.machine_id == machine_id)
        .first()
    )
    if not config:
        raise HTTPException(status_code=404, detail="Sync config not found")

    if not ftp_sync_service:
        raise HTTPException(status_code=503, detail="FTP sync service is not initialized")

    try:
        run_id = await ftp_sync_service.trigger_config_sync(
            config_id=config_id,
            trigger_source="manual",
            relative_paths=payload.relative_paths,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FtpSyncTriggerResponse(run_id=run_id, config_id=config_id, status="queued")


@router.get("/machines/{machine_id}/ftp-sync/runs", response_model=list[FtpSyncRunResponse])
async def list_sync_runs(machine_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """List recent sync runs for one machine."""
    return (
        db.query(FtpSyncRun)
        .filter(FtpSyncRun.machine_id == machine_id)
        .order_by(FtpSyncRun.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/machines/{machine_id}/ftp-sync/runs/{run_id}", response_model=FtpSyncRunDetailResponse)
async def get_sync_run(machine_id: int, run_id: int, db: Session = Depends(get_db)):
    """Get sync run details with per-file item statuses."""
    run = (
        db.query(FtpSyncRun)
        .filter(FtpSyncRun.id == run_id, FtpSyncRun.machine_id == machine_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    items = (
        db.query(FtpSyncRunItem)
        .filter(FtpSyncRunItem.run_id == run.id)
        .order_by(FtpSyncRunItem.id.asc())
        .all()
    )

    return FtpSyncRunDetailResponse(
        id=run.id,
        config_id=run.config_id,
        machine_id=run.machine_id,
        trigger_source=run.trigger_source,
        status=run.status,
        total_files=run.total_files,
        success_files=run.success_files,
        failed_files=run.failed_files,
        conflict_files=run.conflict_files,
        skipped_files=run.skipped_files,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        created_at=run.created_at,
        items=items,
    )


@router.get("/machines/{machine_id}/ftp-sync/conflicts", response_model=list[FtpSyncRunDetailResponse])
async def list_unresolved_conflicts(machine_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """List recent runs that include one or more conflict items."""
    runs = (
        db.query(FtpSyncRun)
        .filter(
            FtpSyncRun.machine_id == machine_id,
            FtpSyncRun.conflict_files > 0,
        )
        .order_by(FtpSyncRun.created_at.desc())
        .limit(limit)
        .all()
    )

    response: list[FtpSyncRunDetailResponse] = []
    for run in runs:
        items = (
            db.query(FtpSyncRunItem)
            .filter(FtpSyncRunItem.run_id == run.id, FtpSyncRunItem.status == "conflict")
            .order_by(FtpSyncRunItem.id.asc())
            .all()
        )
        response.append(
            FtpSyncRunDetailResponse(
                id=run.id,
                config_id=run.config_id,
                machine_id=run.machine_id,
                trigger_source=run.trigger_source,
                status=run.status,
                total_files=run.total_files,
                success_files=run.success_files,
                failed_files=run.failed_files,
                conflict_files=run.conflict_files,
                skipped_files=run.skipped_files,
                started_at=run.started_at,
                completed_at=run.completed_at,
                error_message=run.error_message,
                created_at=run.created_at,
                items=items,
            )
        )

    return response
