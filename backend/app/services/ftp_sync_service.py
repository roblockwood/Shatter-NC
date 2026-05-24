"""Background FTP sync service for local-folder-to-machine upload."""
from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.clients.ftp_client import CNCFtpClient
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.ftp_sync import FtpSyncConfig, FtpSyncFileState, FtpSyncRun, FtpSyncRunItem
from app.models.machine import Machine
from app.utils.ftp_sync_rules import DEFAULT_EXCLUDE_PATTERNS, validate_brother_filename

logger = logging.getLogger(__name__)


class FtpSyncService:
    """Coordinates manual and watcher-triggered FTP sync runs."""

    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self._is_running = False
        self._watcher_task: Optional[asyncio.Task] = None
        self._run_tasks: dict[int, asyncio.Task] = {}
        self._active_run_by_config: dict[int, int] = {}
        self._machine_locks: dict[int, asyncio.Lock] = {}
        self._snapshot_cache: dict[int, dict[str, float]] = {}

    async def start(self):
        """Start local change watcher loop if FTP sync is enabled."""
        if self._is_running:
            return
        if not settings.FTP_SYNC_ENABLED:
            logger.info("FTP sync service disabled by configuration")
            return

        self._reconcile_stale_runs(reason="service_startup")
        self._is_running = True
        if settings.FTP_SYNC_LOCAL_WATCH_ENABLED:
            self._watcher_task = asyncio.create_task(self._watcher_loop())
            logger.info("FTP sync watcher loop started")
        else:
            logger.info("FTP sync watcher disabled (manual trigger only)")

    async def stop(self):
        """Stop watcher and active run tasks."""
        self._is_running = False

        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass
            self._watcher_task = None

        task_ids = list(self._run_tasks.keys())
        for run_id in task_ids:
            task = self._run_tasks.pop(run_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._reconcile_stale_runs(reason="service_shutdown")

        self._active_run_by_config.clear()
        self._snapshot_cache.clear()

    def _reconcile_stale_runs(self, reason: str):
        """Mark dangling queued/in-progress runs as interrupted after restart/stop."""
        db = SessionLocal()
        try:
            stale_runs = (
                db.query(FtpSyncRun)
                .filter(FtpSyncRun.status.in_(["queued", "in_progress"]))
                .all()
            )

            if not stale_runs:
                return

            now = datetime.utcnow()
            for run in stale_runs:
                run.status = "interrupted"
                run.completed_at = run.completed_at or now
                suffix = f"interrupted during {reason}"
                if run.error_message:
                    if suffix not in run.error_message:
                        run.error_message = f"{run.error_message}; {suffix}"
                else:
                    run.error_message = suffix

            db.commit()
            logger.info("Reconciled %s stale FTP sync run(s) as interrupted", len(stale_runs))
        except Exception:
            db.rollback()
            logger.exception("Failed to reconcile stale FTP sync runs")
        finally:
            db.close()

    async def trigger_config_sync(
        self,
        config_id: int,
        trigger_source: str = "manual",
        relative_paths: Optional[list[str]] = None,
    ) -> int:
        """Create a sync run and schedule processing."""
        db = SessionLocal()
        try:
            config = db.query(FtpSyncConfig).filter(FtpSyncConfig.id == config_id).first()
            if not config:
                raise ValueError(f"Sync config {config_id} not found")
            if not config.enabled:
                raise ValueError(f"Sync config {config_id} is disabled")
            if config.id in self._active_run_by_config:
                raise ValueError(f"Sync config {config_id} already has an in-progress run")

            machine = db.query(Machine).filter(Machine.id == config.machine_id).first()
            if not machine:
                raise ValueError(f"Machine {config.machine_id} not found")
            if not machine.ftp_sync_enabled:
                raise ValueError(f"FTP sync is not enabled for machine {config.machine_id}")

            sync_direction = (config.sync_direction or "upload").lower()
            if sync_direction == "download":
                ftp_client = CNCFtpClient(
                    ip_address=machine.ip_address,
                    port=machine.ftp_port,
                    username=machine.ftp_username,
                    password=machine.ftp_password,
                )
                candidate_files, excluded_files = await self._collect_remote_candidate_files(
                    config,
                    ftp_client,
                    relative_paths,
                )
            else:
                candidate_files, excluded_files = self._collect_candidate_files(config, relative_paths)

            run = FtpSyncRun(
                config_id=config.id,
                machine_id=config.machine_id,
                trigger_source=trigger_source,
                status="queued",
                total_files=len(candidate_files) + len(excluded_files),
                skipped_files=len(excluded_files),
            )
            db.add(run)
            db.flush()

            for relative_path, local_path, remote_path in candidate_files:
                db.add(
                    FtpSyncRunItem(
                        run_id=run.id,
                        relative_path=relative_path,
                        local_path=local_path,
                        remote_path=remote_path,
                        status="queued",
                    )
                )

            for relative_path, local_path, remote_path, reason in excluded_files:
                db.add(
                    FtpSyncRunItem(
                        run_id=run.id,
                        relative_path=relative_path,
                        local_path=local_path,
                        remote_path=remote_path,
                        status="skipped",
                        details={"reason": reason},
                    )
                )

            db.commit()
            db.refresh(run)

            self._active_run_by_config[config.id] = run.id
            task = asyncio.create_task(self._process_run(run.id))
            self._run_tasks[run.id] = task
            task.add_done_callback(lambda _: self._run_tasks.pop(run.id, None))
            return run.id
        finally:
            db.close()

    def _collect_candidate_files(
        self,
        config: FtpSyncConfig,
        relative_paths: Optional[list[str]],
    ) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str, str]]]:
        """Build candidate file list from folder + include pattern."""
        root = Path(config.source_folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Source folder does not exist: {config.source_folder}")

        wanted: Optional[set[str]] = None
        if relative_paths:
            wanted = {Path(p).as_posix().lstrip("/") for p in relative_paths}

        files: list[tuple[str, str, str]] = []
        excluded: list[tuple[str, str, str, str]] = []
        exclude_patterns = [
            p.strip() for p in (config.exclude_patterns or "").split(",") if p.strip()
        ] or DEFAULT_EXCLUDE_PATTERNS

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            rel = path.relative_to(root).as_posix()
            if wanted and rel not in wanted:
                continue
            if not fnmatch.fnmatch(path.name, config.include_pattern):
                continue

            remote_path = self._join_remote(config.remote_folder, rel)

            if config.strict_brother_naming and rel.count("/") > self._max_nested_folder_depth(config.control_type):
                excluded.append((rel, str(path), remote_path, "nested_directories_not_supported"))
                continue

            decision = validate_brother_filename(
                path.name,
                control_type=(config.control_type or "C00"),
                strict_naming=bool(config.strict_brother_naming),
                require_onumber=bool(config.require_onumber_filename),
                exclude_patterns=exclude_patterns,
            )
            if not decision.allowed:
                excluded.append((rel, str(path), remote_path, decision.reason or "excluded_by_rules"))
                continue

            files.append((rel, str(path), remote_path))

        return sorted(files, key=lambda x: x[0]), sorted(excluded, key=lambda x: x[0])

    @staticmethod
    def _max_nested_folder_depth(control_type: str | None) -> int:
        """Return max supported folder nesting depth per Brother control profile."""
        mode = (control_type or "C00").upper()
        # C00: root only; D00: up to two folders deep.
        return 2 if mode == "D00" else 0

    async def _collect_remote_candidate_files(
        self,
        config: FtpSyncConfig,
        ftp_client: CNCFtpClient,
        relative_paths: Optional[list[str]],
    ) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str, str]]]:
        """Build candidate file list from remote CNC folder for download mode."""
        root = Path(config.source_folder).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)

        wanted: Optional[set[str]] = None
        if relative_paths:
            wanted = {Path(p).as_posix().lstrip("/") for p in relative_paths}

        remote_files = await self._list_remote_files_recursive(
            ftp_client,
            config.remote_folder,
        )

        files: list[tuple[str, str, str]] = []
        excluded: list[tuple[str, str, str, str]] = []
        exclude_patterns = [
            p.strip() for p in (config.exclude_patterns or "").split(",") if p.strip()
        ] or DEFAULT_EXCLUDE_PATTERNS

        for entry in remote_files:
            if entry.get("is_directory"):
                continue

            name = entry.get("name")
            if not name:
                continue
            if not fnmatch.fnmatch(name, config.include_pattern):
                continue

            remote_path = entry.get("path") or self._join_remote(config.remote_folder, name)
            rel = self._relative_remote_path(config.remote_folder, remote_path)
            if wanted and rel not in wanted:
                continue
            local_path = str(root / rel)

            decision = validate_brother_filename(
                name,
                control_type=(config.control_type or "C00"),
                strict_naming=bool(config.strict_brother_naming),
                require_onumber=bool(config.require_onumber_filename),
                exclude_patterns=exclude_patterns,
            )
            if not decision.allowed:
                excluded.append((rel, local_path, remote_path, decision.reason or "excluded_by_rules"))
                continue

            files.append((rel, local_path, remote_path))

        return sorted(files, key=lambda x: x[0]), sorted(excluded, key=lambda x: x[0])

    async def _list_remote_files_recursive(
        self,
        ftp_client: CNCFtpClient,
        start_folder: str,
        max_depth: int = 10,
    ) -> list[dict]:
        """Recursively list remote files under a folder for download mode."""
        queue: list[tuple[str, int]] = [(start_folder, 0)]
        visited: set[str] = set()
        seen_files: set[str] = set()
        results: list[dict] = []

        while queue:
            folder, depth = queue.pop(0)
            if folder in visited:
                continue
            visited.add(folder)

            entries = await self._list_remote_files_with_retry(ftp_client, folder)
            for entry in entries:
                path = entry.get("path")
                if not path:
                    continue
                if entry.get("is_directory"):
                    if depth < max_depth:
                        queue.append((path, depth + 1))
                    continue
                # Some FTP servers can return duplicate file rows across recursive listings
                # (or, in tests, a folder listing stub may not scope by folder). Deduplicate
                # by the full remote path so downstream candidate selection is stable.
                if path in seen_files:
                    continue
                seen_files.add(path)
                results.append(entry)

        return results

    @staticmethod
    def _relative_remote_path(remote_root: str, remote_path: str) -> str:
        """Return relative path from remote root for nested download mapping."""
        root = (remote_root or "/").rstrip("/") or "/"
        if root == "/":
            return remote_path.lstrip("/")
        if remote_path.startswith(f"{root}/"):
            return remote_path[len(root) + 1 :]
        return remote_path.lstrip("/")

    async def _watcher_loop(self):
        """Scan enabled configs and trigger sync runs on changed files."""
        while self._is_running:
            await asyncio.sleep(settings.FTP_SYNC_SCAN_INTERVAL_SECONDS)
            db = SessionLocal()
            try:
                configs = (
                    db.query(FtpSyncConfig)
                    .join(Machine, FtpSyncConfig.machine_id == Machine.id)
                    .filter(FtpSyncConfig.enabled == True, Machine.ftp_sync_enabled == True)
                    .all()
                )
            finally:
                db.close()

            for config in configs:
                try:
                    if (config.sync_direction or "upload").lower() != "upload":
                        continue
                    changed_files = self._detect_changed_files(config)
                    if not changed_files:
                        continue
                    if config.id in self._active_run_by_config:
                        continue
                    await self.trigger_config_sync(
                        config_id=config.id,
                        trigger_source="watcher",
                        relative_paths=changed_files,
                    )
                except Exception as exc:
                    logger.warning("Watcher sync detection failed for config %s: %s", config.id, exc)

    def _detect_changed_files(self, config: FtpSyncConfig) -> list[str]:
        """Return relative paths that changed since last scan."""
        root = Path(config.source_folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return []

        previous = self._snapshot_cache.get(config.id, {})
        current: dict[str, float] = {}
        changed: list[str] = []

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if not fnmatch.fnmatch(file_path.name, config.include_pattern):
                continue

            relative_path = file_path.relative_to(root).as_posix()
            mtime = file_path.stat().st_mtime
            current[relative_path] = mtime

            last_mtime = previous.get(relative_path)
            if last_mtime is not None and mtime > (last_mtime + config.debounce_seconds):
                changed.append(relative_path)

        # First observation seeds cache but should not enqueue a full-folder sync run.
        if config.id not in self._snapshot_cache:
            self._snapshot_cache[config.id] = current
            return []

        self._snapshot_cache[config.id] = current
        return changed

    async def _process_run(self, run_id: int):
        """Process each item in a run and update statuses/counters."""
        db = SessionLocal()
        run = db.query(FtpSyncRun).filter(FtpSyncRun.id == run_id).first()
        if not run:
            db.close()
            return

        config = db.query(FtpSyncConfig).filter(FtpSyncConfig.id == run.config_id).first()
        machine = db.query(Machine).filter(Machine.id == run.machine_id).first()

        if not config or not machine:
            run.status = "failed"
            run.error_message = "Config or machine was removed before run started"
            run.completed_at = datetime.utcnow()
            db.commit()
            db.close()
            return

        lock = self._machine_locks.setdefault(machine.id, asyncio.Lock())

        try:
            async with lock:
                run.status = "in_progress"
                run.started_at = datetime.utcnow()
                db.commit()
                await self._broadcast_progress(machine.id, run)

                ftp_client = CNCFtpClient(
                    ip_address=machine.ip_address,
                    port=machine.ftp_port,
                    username=machine.ftp_username,
                    password=machine.ftp_password,
                )

                sync_direction = (config.sync_direction or "upload").lower()
                remote_name_set: set[str] = set()
                if sync_direction == "upload":
                    await self._ensure_remote_directory_ready(ftp_client, config.remote_folder)
                    remote_files = await self._list_remote_files_with_retry(ftp_client, config.remote_folder)
                    remote_name_set = {entry.get("name") for entry in remote_files if entry.get("name")}

                items = (
                    db.query(FtpSyncRunItem)
                    .filter(FtpSyncRunItem.run_id == run.id, FtpSyncRunItem.status == "queued")
                    .order_by(FtpSyncRunItem.id.asc())
                    .all()
                )

                run_tool_data: dict | None = None
                if config.auto_validate:
                    run_tool_data = await self._prefetch_tool_data(machine.id)

                for item in items:
                    try:
                        await self._process_item(
                            db,
                            config,
                            machine,
                            run,
                            item,
                            ftp_client,
                            remote_name_set,
                            run_tool_data,
                        )
                        db.commit()
                    except Exception as item_exc:
                        # Keep long runs moving even if one item poisons the transaction state.
                        db.rollback()

                        item = db.query(FtpSyncRunItem).filter(FtpSyncRunItem.id == item.id).first()
                        run = db.query(FtpSyncRun).filter(FtpSyncRun.id == run.id).first()
                        if item is not None and run is not None:
                            item.status = "failed"
                            item.error_message = f"Item processing failed: {item_exc}"
                            run.failed_files += 1
                            db.commit()

                    await self._broadcast_progress(machine.id, run)

                if run.failed_files > 0:
                    run.status = "failed" if run.success_files == 0 else "completed"
                elif run.conflict_files > 0:
                    run.status = "completed_with_conflicts"
                else:
                    run.status = "completed"
                run.completed_at = datetime.utcnow()
                db.commit()
                await self._broadcast_progress(machine.id, run, final=True)
        except Exception as exc:
            logger.exception("Sync run failed")
            # Clear failed transaction state (e.g., flush/serialization errors)
            # before writing final run status.
            db.rollback()
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()
            await self._broadcast_progress(machine.id, run, final=True)
        finally:
            self._active_run_by_config.pop(config.id, None)
            db.close()

    async def _process_item(
        self,
        db: Session,
        config: FtpSyncConfig,
        machine: Machine,
        run: FtpSyncRun,
        item: FtpSyncRunItem,
        ftp_client: CNCFtpClient,
        remote_name_set: set[str],
        run_tool_data: dict | None = None,
    ):
        """Run validation + upload + registration for a single file."""
        sync_direction = (config.sync_direction or "upload").lower()

        if sync_direction == "download":
            await self._process_item_download(db, config, machine, run, item, ftp_client)
            return

        local_path = Path(item.local_path)
        if not local_path.exists() or not local_path.is_file():
            item.status = "failed"
            item.error_message = "Local file no longer exists"
            run.failed_files += 1
            return

        local_bytes = local_path.read_bytes()
        content_hash = hashlib.sha256(local_bytes).hexdigest()
        item.content_hash = content_hash

        file_state = (
            db.query(FtpSyncFileState)
            .filter(
                FtpSyncFileState.config_id == config.id,
                FtpSyncFileState.relative_path == item.relative_path,
            )
            .first()
        )

        remote_name = Path(item.remote_path).name
        remote_exists = remote_name in remote_name_set

        if remote_exists and (not file_state or file_state.last_uploaded_hash != content_hash):
            item.status = "conflict"
            item.error_message = "Remote file exists with unknown or different hash"
            item.details = {
                "resolution_required": True,
                "policy": "manual",
            }
            run.conflict_files += 1
            return

        if file_state and file_state.last_uploaded_hash == content_hash:
            item.status = "skipped"
            item.details = {
                "reason": "unchanged_content",
            }
            run.skipped_files += 1
            return

        item.status = "validating"

        validation_payload = None
        gcode_content = local_bytes.decode("utf-8", errors="replace")
        try:
            if config.auto_validate:
                from app.api.programs import ProgramValidateRequest, validate_program

                validation_result = await validate_program(
                    machine_id=machine.id,
                    request=ProgramValidateRequest(
                        gcode_content=gcode_content,
                        prefetched_tool_data=run_tool_data,
                    ),
                    db=db,
                )
                validation_payload = jsonable_encoder(validation_result.model_dump())
                item.details = {
                    "validation": validation_payload,
                }
        except Exception as exc:
            db.rollback()
            item.status = "failed"
            item.error_message = f"Validation failed: {exc}"
            run.failed_files += 1
            return

        item.status = "uploading"
        upload_result = await self._upload_with_retry(
            ftp_client,
            local_bytes,
            item.remote_path,
        )
        if not upload_result.get("success"):
            item.status = "failed"
            item.error_message = upload_result.get("error", "FTP upload failed")
            run.failed_files += 1
            return

        if config.auto_register:
            try:
                from app.api.programs import upload_program
                from app.schemas.program import ProgramUploadRequest

                await upload_program(
                    request=ProgramUploadRequest(
                        gcode_content=gcode_content,
                        original_filename=local_path.name,
                        machine_id=machine.id,
                        deployed_filename=Path(item.remote_path).name,
                        deployed_path=item.remote_path,
                        validate_before_upload=config.auto_validate,
                        validation_results=validation_payload,
                    ),
                    db=db,
                )
            except Exception as exc:
                db.rollback()
                item.status = "failed"
                item.error_message = f"Program registration failed: {exc}"
                run.failed_files += 1
                return

        if not file_state:
            file_state = FtpSyncFileState(
                config_id=config.id,
                relative_path=item.relative_path,
                last_uploaded_hash=content_hash,
                last_uploaded_remote_path=item.remote_path,
            )
            db.add(file_state)
        else:
            file_state.last_uploaded_hash = content_hash
            file_state.last_uploaded_remote_path = item.remote_path
            file_state.last_uploaded_at = datetime.utcnow()

        item.status = "registered" if config.auto_register else "uploaded"
        run.success_files += 1

    async def _process_item_download(
        self,
        db: Session,
        config: FtpSyncConfig,
        machine: Machine,
        run: FtpSyncRun,
        item: FtpSyncRunItem,
        ftp_client: CNCFtpClient,
    ):
        """Download a CNC file to local folder with conflict checks."""
        item.status = "downloading"
        remote_bytes = await self._download_with_retry(ftp_client, item.remote_path)
        if remote_bytes is None:
            item.status = "failed"
            item.error_message = "FTP download failed"
            run.failed_files += 1
            return

        content_hash = hashlib.sha256(remote_bytes).hexdigest()
        item.content_hash = content_hash

        file_state = (
            db.query(FtpSyncFileState)
            .filter(
                FtpSyncFileState.config_id == config.id,
                FtpSyncFileState.relative_path == item.relative_path,
            )
            .first()
        )

        local_path = Path(item.local_path)
        if local_path.exists() and local_path.is_file():
            local_bytes = local_path.read_bytes()
            local_hash = hashlib.sha256(local_bytes).hexdigest()

            if file_state and file_state.last_uploaded_hash == content_hash and local_hash == content_hash:
                item.status = "skipped"
                item.details = {"reason": "unchanged_content"}
                run.skipped_files += 1
                return

            if local_hash != content_hash and (not file_state or file_state.last_uploaded_hash != local_hash):
                item.status = "conflict"
                item.error_message = "Local file changed outside sync; manual resolution required"
                item.details = {
                    "resolution_required": True,
                    "policy": "manual",
                    "reason": "local_modified",
                }
                run.conflict_files += 1
                return

        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(remote_bytes)

        # Download mode prioritizes reliable file copy to local disk. Validation and
        # registration can be run separately from the local file set if needed.
        if config.auto_validate or config.auto_register:
            details = dict(item.details or {})
            details["post_processing_skipped"] = True
            details["post_processing_reason"] = "download_mode_copy_priority"
            item.details = details

        if not file_state:
            file_state = FtpSyncFileState(
                config_id=config.id,
                relative_path=item.relative_path,
                last_uploaded_hash=content_hash,
                last_uploaded_remote_path=item.remote_path,
            )
            db.add(file_state)
        else:
            file_state.last_uploaded_hash = content_hash
            file_state.last_uploaded_remote_path = item.remote_path
            file_state.last_uploaded_at = datetime.utcnow()

        item.status = "downloaded"
        run.success_files += 1

    async def _broadcast_progress(self, machine_id: int, run: FtpSyncRun, final: bool = False):
        """Publish sync progress via existing status websocket stream."""
        payload = {
            "machine_id": machine_id,
            "ftp_sync": {
                "run_id": run.id,
                "config_id": run.config_id,
                "status": run.status,
                "trigger_source": run.trigger_source,
                "total_files": run.total_files,
                "success_files": run.success_files,
                "failed_files": run.failed_files,
                "conflict_files": run.conflict_files,
                "skipped_files": run.skipped_files,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "final": final,
            },
        }
        try:
            await self.websocket_manager.broadcast_status(payload)
        except Exception as exc:
            logger.debug("Unable to broadcast FTP sync update: %s", exc)

    async def _ensure_remote_directory_ready(self, ftp_client: CNCFtpClient, remote_folder: str):
        """Create target directory if missing and allow CNC FTP state to settle."""
        result = await ftp_client.ensure_directory(
            remote_folder,
            retries=settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES,
            settle_delay_seconds=settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS,
        )
        if not result.get("success"):
            raise ValueError(
                f"Failed to ensure remote directory {remote_folder}: {result.get('error', 'unknown error')}"
            )

    async def _list_remote_files_with_retry(self, ftp_client: CNCFtpClient, remote_folder: str):
        """List remote files with one or more retries for new directory propagation delays."""
        attempts = settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES + 1
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                return await ftp_client.list_files(remote_folder)
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                await asyncio.sleep(settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS)
        raise ValueError(f"Unable to list remote folder {remote_folder}: {last_error}")

    async def _upload_with_retry(self, ftp_client: CNCFtpClient, local_bytes: bytes, remote_path: str):
        """Upload with retry to handle transient remote folder creation timing failures."""
        attempts = settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES + 1
        last_result = None
        for attempt in range(1, attempts + 1):
            last_result = await ftp_client.upload_file(local_bytes, remote_path)
            if last_result.get("success"):
                return last_result
            if attempt >= attempts:
                break
            await asyncio.sleep(settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS)
        return last_result or {
            "success": False,
            "error": "FTP upload failed after retries",
        }

    async def _download_with_retry(self, ftp_client: CNCFtpClient, remote_path: str) -> Optional[bytes]:
        """Download with retry for transient CNC FTP read failures."""
        attempts = settings.FTP_SYNC_REMOTE_DIR_CREATE_RETRIES + 1
        for attempt in range(1, attempts + 1):
            data = await ftp_client.download_file(remote_path)
            if data is not None:
                return data
            if attempt >= attempts:
                break
            await asyncio.sleep(settings.FTP_SYNC_REMOTE_DIR_CREATE_DELAY_SECONDS)
        return None

    @staticmethod
    def _join_remote(remote_folder: str, relative_path: str) -> str:
        """Join remote base path and relative file path with forward slashes."""
        normalized_folder = (remote_folder or "/").rstrip("/")
        normalized_rel = relative_path.lstrip("/").replace("\\", "/")
        if not normalized_folder:
            return f"/{normalized_rel}"
        return f"{normalized_folder}/{normalized_rel}"

    async def _prefetch_tool_data(self, machine_id: int) -> dict:
        """Fetch machine tool data once for a sync run (best-effort)."""
        from app.api import status as status_api

        # Fast path: WebSocket cache already has tool data.
        if self.websocket_manager:
            try:
                cached = self.websocket_manager.get_machine_status(machine_id) or {}
                if cached.get("tools"):
                    logger.debug(
                        "Machine %d - sync prefetch: %d tools from WebSocket cache",
                        machine_id,
                        len(cached["tools"]),
                    )
                    return {"tools": cached["tools"]}
            except Exception:
                pass

        # Trigger a single polling-service refresh to populate the cache.
        if status_api.polling_service:
            try:
                tool_data = await status_api.polling_service.refresh_tool_data(machine_id)
                tools = (tool_data or {}).get("tools", [])
                if tools:
                    logger.info(
                        "Machine %d - sync prefetch: %d tools loaded via polling service",
                        machine_id,
                        len(tools),
                    )
                    return {"tools": tools}
                logger.warning(
                    "Machine %d - sync prefetch: polling service returned no tools; "
                    "validation will proceed without tool data",
                    machine_id,
                )
            except Exception as exc:
                logger.warning("Machine %d - sync prefetch: polling service error: %s", machine_id, exc)

        return {"tools": []}
