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
    patch_tool_names,
    tool_names_match,
)

logger = logging.getLogger(__name__)


def _resolve_toln_filename(units: str) -> str:
    return "TOLNI1.NC" if units == "in" else "TOLNM1.NC"


async def _read_toln_via_telnet(
    db_machine: Machine,
    telnet_client: CNCTelnetClient | None = None,
) -> Tuple[str, CNCTelnetClient | None, bool]:
    """Return (content, client, owns_client)."""
    owns = telnet_client is None
    client = telnet_client
    if client is None:
        client = await create_fresh_connection(
            ip_address=db_machine.ip_address,
            port=10000,
            timeout=10,
        )
    units = db_machine.units or "in"
    content = await client.get_tool_table_data(units=units, verbose=False)
    if not content:
        if owns and client:
            await client.disconnect()
        raise RuntimeError("Failed to read tool table via telnet LOD")
    return content, client, owns


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

    content, client, owns_client = await _read_toln_via_telnet(db_machine, telnet_client)
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

    ftp = CNCFtpClient(
        ip_address=db_machine.ip_address,
        port=db_machine.ftp_port or 21,
        username=db_machine.ftp_username or "anonymous",
        password=db_machine.ftp_password or "anonymous",
    )
    try:
        upload = await ftp.upload_file(patched.encode("utf-8"), filename)
        if not upload.get("success"):
            raise RuntimeError(upload.get("error") or "FTP upload failed")
    finally:
        await ftp.disconnect()

    verify_content = await client.get_tool_table_data(units=units, verbose=False)
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

    if owns_client and client:
        await client.disconnect()

    return old_names, verified
