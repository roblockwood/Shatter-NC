#!/usr/bin/env python3
"""
Re-parse all registered programs from machine FTP and update program_metadata in place.

Run this inside the backend container when the G-code parser has been updated and you
want to refresh the stored metadata without re-uploading files:

    docker exec -it shatter-backend python scripts/reparse_all_programs.py

By default only programs that have a current deployment (is_current=True) are processed,
since those are the ones we can actually fetch. Programs with no deployment are skipped
and reported at the end.

Flags:
    --dry-run   Parse and print what would change without writing to the DB.
    --machine N Only process programs deployed on machine with id=N.
"""
import asyncio
import hashlib
import sys
from pathlib import Path

# Ensure the backend package is importable when run from repo root inside the container.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.program import Program, ProgramDeployment
from app.models.machine import Machine
from app.clients.ftp_client import CNCFtpClient
from app.parsers.gcode_parser import parse_gcode

import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _build_updated_metadata(parsed: dict, existing: dict) -> dict:
    """Merge freshly-parsed metadata into the existing JSONB blob.

    Only fields that the parser actually produces are replaced; any custom
    keys that have been written by other parts of the system are preserved.
    """
    updated = dict(existing or {})
    for key in ("tools", "wcs_offset", "stock_size", "posted_date",
                 "estimated_runtime_seconds", "line_count", "file_size"):
        if key in parsed:
            updated[key] = parsed[key]
    return updated


async def reparse_program(
    db: Session,
    program: Program,
    deployment: ProgramDeployment,
    machine: Machine,
    dry_run: bool,
) -> str:
    """Fetch one file from FTP and update program_metadata. Returns a status string."""
    ftp = CNCFtpClient(
        ip_address=machine.ip_address,
        port=machine.ftp_port,
        username=machine.ftp_username,
        password=machine.ftp_password,
    )
    try:
        raw_bytes = await ftp.download_file(deployment.deployed_path)
    except Exception as exc:
        return f"FTP_ERROR: {exc}"
    finally:
        try:
            if ftp.ftp:
                ftp.ftp.quit()
        except Exception:
            pass

    if raw_bytes is None:
        return "FTP_EMPTY"

    # Verify the file on disk still matches what we registered.
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    if actual_hash != program.content_hash:
        return f"HASH_MISMATCH (expected {program.content_hash[:10]}… got {actual_hash[:10]}…)"

    try:
        gcode_content = raw_bytes.decode("utf-8", errors="replace")
        parsed = parse_gcode(gcode_content)
    except Exception as exc:
        return f"PARSE_ERROR: {exc}"

    new_metadata = _build_updated_metadata(parsed, program.program_metadata)

    # Ensure datetime values are serialized to ISO strings for JSONB storage
    from datetime import datetime as _dt
    if isinstance(new_metadata.get("posted_date"), _dt):
        new_metadata["posted_date"] = new_metadata["posted_date"].isoformat()

    if new_metadata == program.program_metadata:
        return "UNCHANGED"

    if dry_run:
        old_tool_count = len((program.program_metadata or {}).get("tools", []))
        new_tool_count = len(new_metadata.get("tools", []))
        return f"WOULD_UPDATE (tools: {old_tool_count} -> {new_tool_count})"

    program.program_metadata = new_metadata
    db.commit()
    return "UPDATED"


async def main(machine_id_filter: int | None, dry_run: bool) -> None:
    db: Session = SessionLocal()
    try:
        # One query: join programs -> current deployments -> machines
        query = (
            db.query(Program, ProgramDeployment, Machine)
            .join(ProgramDeployment, ProgramDeployment.program_id == Program.id)
            .join(Machine, Machine.id == ProgramDeployment.machine_id)
            .filter(ProgramDeployment.is_current.is_(True))
            .filter(Program.is_active.is_(True))
        )
        if machine_id_filter is not None:
            query = query.filter(Machine.id == machine_id_filter)

        rows = query.all()

        # Multiple deployments can point at the same program (different machines). We
        # only need to fetch-and-reparse once per unique program_id; pick the first
        # deployment we encounter.
        seen: dict[int, tuple[Program, ProgramDeployment, Machine]] = {}
        for program, deployment, machine in rows:
            if program.id not in seen:
                seen[program.id] = (program, deployment, machine)

        all_program_ids = {p.id for p in db.query(Program).filter(Program.is_active.is_(True)).all()}
        deployed_ids = set(seen.keys())
        undeployable = all_program_ids - deployed_ids

        logger.info(
            "Found %d programs with current deployments; %d have no deployment.",
            len(seen),
            len(undeployable),
        )
        if dry_run:
            logger.info("DRY RUN — no DB writes will occur.")

        results: dict[str, list[str]] = {"UPDATED": [], "UNCHANGED": [], "WOULD_UPDATE": [], "SKIPPED": []}
        errors: list[tuple[str, str]] = []

        for program, deployment, machine in seen.values():
            label = f"{program.original_filename} (id={program.id}, machine={machine.name}, path={deployment.deployed_path})"
            status = await reparse_program(db, program, deployment, machine, dry_run)
            if status.startswith("WOULD_UPDATE"):
                results["WOULD_UPDATE"].append(f"{label}: {status}")
            elif status == "UPDATED":
                results["UPDATED"].append(label)
            elif status == "UNCHANGED":
                results["UNCHANGED"].append(label)
            else:
                errors.append((label, status))

        # Summary
        print("\n" + "=" * 70)
        print(f"  UPDATED  : {len(results['UPDATED'])}")
        print(f"  WOULD_UPDATE: {len(results['WOULD_UPDATE'])}" if dry_run else "")
        print(f"  UNCHANGED: {len(results['UNCHANGED'])}")
        print(f"  ERRORS   : {len(errors)}")
        print(f"  NO DEPLOYMENT: {len(undeployable)}")
        print("=" * 70)

        for label in results["UPDATED"]:
            print(f"  [UPDATED]   {label}")
        for label in results["WOULD_UPDATE"]:
            print(f"  [DRY]       {label}")
        for label, err in errors:
            print(f"  [ERROR]     {label}: {err}")
        if undeployable:
            print(f"\n  Programs with no current deployment ({len(undeployable)} total):")
            for pid in sorted(undeployable):
                p = db.query(Program).filter(Program.id == pid).first()
                print(f"    id={pid}  {p.original_filename if p else '?'}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing.")
    parser.add_argument("--machine", type=int, default=None, metavar="ID", help="Limit to one machine id.")
    args = parser.parse_args()

    asyncio.run(main(machine_id_filter=args.machine, dry_run=args.dry_run))
