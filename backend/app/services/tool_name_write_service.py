"""Write tool names to the machine via TOLN FTP upload."""
from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from app.clients.ftp_client import CNCFtpClient
from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.models.machine import Machine
from app.parsers.atctl_parser_v2 import parse_atctl_v2
from app.parsers.tolni_parser_v2 import parse_tolni_v2
from app.services.tolni_patch import (
    collect_tool_names,
    count_toln_line_prefixes,
    patch_tool_names,
    tool_names_match,
)

logger = logging.getLogger(__name__)

_ATC_LOD_FALLBACK_FILENAME = {
    "C00": "ATCTL.NC",
    "D00": "ATCTLD.NC",
}


def _resolve_toln_filename(units: str) -> str:
    return "TOLNI1.NC" if units == "in" else "TOLNM1.NC"


def _control_version(machine: Machine) -> str:
    return (machine.control_version or "C00").upper()


def _ftp_client_for_machine(db_machine: Machine) -> CNCFtpClient:
    return CNCFtpClient(
        ip_address=db_machine.ip_address,
        port=db_machine.ftp_port or 21,
        username=db_machine.ftp_username or "anonymous",
        password=db_machine.ftp_password or "anonymous",
    )


def count_atc_pot_assignments(atc_content: str, control_version: str) -> int:
    """Count magazine pots with a real tool assigned (excludes spindle/cap/empty)."""
    parsed = parse_atctl_v2(
        atc_content.encode("utf-8"),
        control_version=control_version,
    )
    count = 0
    for row in parsed.get("tools") or []:
        pot = row.get("pot_number")
        if pot is not None and str(pot).upper() == "SPINDLE":
            continue
        tool_num = row.get("tool_number") or 0
        if tool_num > 0 and tool_num not in (255, 999):
            count += 1
    return count


async def _read_atc_backup(
    db_machine: Machine,
    ftp: CNCFtpClient,
    telnet_client: CNCTelnetClient | None,
) -> Tuple[str, str, int]:
    """
    Backup ATC magazine before TOLN upload.

    Pot assignments live in ATCTL, not TOLN. Uploading TOLNI1.NC can reset ATCTL on
    the control — we must snapshot and restore magazine data around name writes.
    """
    control_version = _control_version(db_machine)
    content, filename = await ftp.get_atc_magazine_file(control_version=control_version)

    source = "FTP"
    if not content and telnet_client is not None:
        content = await telnet_client.get_atc_magazine_data(
            control_version=control_version,
            verbose=False,
        )
        filename = _ATC_LOD_FALLBACK_FILENAME.get(control_version, "ATCTL.NC")
        source = "telnet LOD"

    if not content:
        raise RuntimeError(
            "Cannot backup ATCTL magazine before TOLN name upload — aborting to prevent pot loss"
        )

    assignments = count_atc_pot_assignments(content, control_version)
    logger.info(
        "Backed up %s for machine %s via %s (%s pot assignment(s), %s chars)",
        filename,
        db_machine.id,
        source,
        assignments,
        len(content),
    )
    return content, filename, assignments


async def _restore_atc_backup(
    db_machine: Machine,
    ftp: CNCFtpClient,
    atc_content: str,
    atc_filename: str,
    expected_assignments: int,
    telnet_client: CNCTelnetClient | None,
) -> None:
    control_version = _control_version(db_machine)
    logger.info(
        "Restoring %s for machine %s after TOLN name upload (expect %s assignment(s))",
        atc_filename,
        db_machine.id,
        expected_assignments,
    )
    upload = await ftp.upload_file(atc_content.encode("utf-8"), atc_filename)
    if not upload.get("success"):
        raise RuntimeError(upload.get("error") or f"Failed to restore {atc_filename}")

    verify_client = telnet_client
    owns_verify = False
    if verify_client is None:
        verify_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )
        owns_verify = True
    try:
        verify_atc = await verify_client.get_atc_magazine_data(
            control_version=control_version,
            verbose=False,
        )
        if not verify_atc:
            raise RuntimeError("Failed to verify ATCTL after restore upload")
        restored = count_atc_pot_assignments(verify_atc, control_version)
        if expected_assignments > 0 and restored < expected_assignments:
            raise RuntimeError(
                f"ATCTL restore incomplete: expected {expected_assignments} pot assignment(s), "
                f"read back {restored}"
            )
        logger.info(
            "Restored %s for machine %s (%s pot assignment(s) verified)",
            atc_filename,
            db_machine.id,
            restored,
        )
    finally:
        if owns_verify and verify_client:
            await verify_client.disconnect()


async def _read_toln_via_ftp(
    db_machine: Machine,
    ftp_client: CNCFtpClient | None = None,
) -> Tuple[str, CNCFtpClient, bool]:
    """
    Read the on-disk TOLN file via FTP.

    Telnet LOD often returns only T## offset rows. Never use LOD content as an upload source.
    """
    owns = ftp_client is None
    ftp = ftp_client or _ftp_client_for_machine(db_machine)
    units = db_machine.units or "in"
    filename = _resolve_toln_filename(units)

    content = await ftp.get_tool_table_data(units=units)
    if not content:
        raise RuntimeError(
            f"Failed to read {filename} via FTP — full file required before TOLN name upload"
        )

    counts = count_toln_line_prefixes(content)
    logger.info(
        "Read %s via FTP for machine %s: T=%s M=%s V=%s Y=%s (%s chars)",
        filename,
        db_machine.id,
        counts["T"],
        counts["M"],
        counts["V"],
        counts["Y"],
        len(content),
    )
    return content, ftp, owns


async def write_tool_names_via_ftp(
    db_machine: Machine,
    updates: Dict[int, str],
    telnet_client: CNCTelnetClient | None = None,
) -> Tuple[Dict[int, str], Dict[int, bool]]:
    """
    Patch tool names in TOLN and upload via FTP.

    ATCTL magazine data is backed up and restored around the TOLN upload because the
    control clears pot assignments when TOLNI1/TOLNM1 is replaced.
    """
    if not updates:
        return {}, {}

    units = db_machine.units or "in"
    filename = _resolve_toln_filename(units)

    ftp = _ftp_client_for_machine(db_machine)
    try:
        atc_backup, atc_filename, atc_assignments = await _read_atc_backup(
            db_machine, ftp, telnet_client
        )

        content, ftp, _owns_ftp = await _read_toln_via_ftp(db_machine, ftp)
        old_names = collect_tool_names(content, updates.keys())
        patched = patch_tool_names(content, updates)
        if patched == content:
            logger.info(
                "TOLN name patch produced identical content for machine %s; skipping upload",
                db_machine.id,
            )
            return old_names, {tn: True for tn in updates}

        logger.info(
            "Uploading patched %s for machine %s (%s tool name change(s))",
            filename,
            db_machine.id,
            len(updates),
        )
        upload = await ftp.upload_file(patched.encode("utf-8"), filename)
        if not upload.get("success"):
            raise RuntimeError(upload.get("error") or "FTP upload failed")

        await _restore_atc_backup(
            db_machine,
            ftp,
            atc_backup,
            atc_filename,
            atc_assignments,
            telnet_client,
        )
    finally:
        await ftp.disconnect()

    verify_client = telnet_client
    owns_verify = False
    if verify_client is None:
        verify_client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )
        owns_verify = True

    try:
        verify_content = await verify_client.get_tool_table_data(units=units, verbose=False)
        if not verify_content:
            raise RuntimeError("Failed to verify tool table after FTP upload")

        parsed = parse_tolni_v2(
            verify_content.encode("utf-8"),
            units=units,
            control_version=db_machine.control_version,
        )
        by_number = {t["tool_number"]: t.get("tool_name", "") for t in parsed.get("tools", [])}

        verified: Dict[int, bool] = {}
        for tool_number, new_name in updates.items():
            actual = by_number.get(tool_number, "")
            verified[tool_number] = tool_names_match(new_name, actual or "")
            if not verified[tool_number]:
                logger.warning(
                    "Tool T%02d name verify failed: expected %r, got %r",
                    tool_number,
                    new_name,
                    actual,
                )
    finally:
        if owns_verify and verify_client:
            await verify_client.disconnect()

    return old_names, verified
