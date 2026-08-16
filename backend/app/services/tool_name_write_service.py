"""Write tool names to the machine via TOLN FTP upload."""
from __future__ import annotations

import logging
from typing import Dict, Tuple

from app.clients.ftp_client import CNCFtpClient
from app.clients.telnet_client import CNCTelnetClient, create_fresh_connection
from app.models.machine import Machine
from app.parsers.tolni_parser_v2 import parse_tolni_v2
from app.services.tolni_patch import (
    collect_tool_names,
    count_toln_line_prefixes,
    patch_tool_names,
    tool_names_match,
)

logger = logging.getLogger(__name__)


def _resolve_toln_filename(units: str) -> str:
    return "TOLNI1.NC" if units == "in" else "TOLNM1.NC"


def _ftp_client_for_machine(db_machine: Machine) -> CNCFtpClient:
    return CNCFtpClient(
        ip_address=db_machine.ip_address,
        port=db_machine.ftp_port or 21,
        username=db_machine.ftp_username or "anonymous",
        password=db_machine.ftp_password or "anonymous",
    )


async def _read_toln_via_ftp(
    db_machine: Machine,
    ftp_client: CNCFtpClient | None = None,
) -> Tuple[str, CNCFtpClient, bool]:
    """
    Read the on-disk TOLN file via FTP.

    Telnet LOD often returns only T## offset rows. Uploading that truncated payload
    as TOLNI1.NC wipes M## magazine (and V/Y) sections and clears ATC on the control.
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
    logger.debug(
        "Read %s via FTP for machine %s: T=%s M=%s V=%s Y=%s chars=%s",
        filename,
        db_machine.id,
        counts["T"],
        counts["M"],
        counts["V"],
        counts["Y"],
        len(content),
    )
    return content, ftp, owns


async def _warn_if_telnet_lod_truncated(
    db_machine: Machine,
    ftp_content: str,
    telnet_client: CNCTelnetClient | None,
) -> None:
    """Log when telnet LOD omits magazine rows present in the FTP file (diagnostic)."""
    if telnet_client is None:
        return
    units = db_machine.units or "in"
    lod = await telnet_client.get_tool_table_data(units=units, verbose=False)
    if not lod:
        return
    ftp_counts = count_toln_line_prefixes(ftp_content)
    lod_counts = count_toln_line_prefixes(lod)
    if lod_counts["M"] < ftp_counts["M"] or len(lod) < len(ftp_content) * 0.9:
        logger.warning(
            "Machine %s telnet LOD TOLN appears truncated vs FTP (LOD M=%s FTP M=%s; "
            "LOD %s chars vs FTP %s chars). Never upload LOD content.",
            db_machine.id,
            lod_counts["M"],
            ftp_counts["M"],
            len(lod),
            len(ftp_content),
        )


async def write_tool_names_via_ftp(
    db_machine: Machine,
    updates: Dict[int, str],
    telnet_client: CNCTelnetClient | None = None,
) -> Tuple[Dict[int, str], Dict[int, bool]]:
    """
    Patch tool names in TOLN and upload via FTP.

    Returns:
        old_names: tool_number -> previous name (normalized display form)
        verified: tool_number -> True if LOD readback matches requested name
    """
    if not updates:
        return {}, {}

    units = db_machine.units or "in"
    filename = _resolve_toln_filename(units)

    ftp = _ftp_client_for_machine(db_machine)
    owns_ftp = True
    try:
        content, ftp, owns_ftp = await _read_toln_via_ftp(db_machine, ftp)
        await _warn_if_telnet_lod_truncated(db_machine, content, telnet_client)

        old_names = collect_tool_names(content, updates.keys())
        patched = patch_tool_names(content, updates)
        if patched == content:
            logger.info("TOLN name patch produced identical content; skipping FTP upload")
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
    finally:
        if owns_ftp:
            await ftp.disconnect()

    # Verify tool name via telnet LOD (read-only; does not source the upload).
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
