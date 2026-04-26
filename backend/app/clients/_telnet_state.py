"""Module-level shared state and protocol constants for the CNC telnet client.

This module holds the asyncio locks, per-machine connection registry, and
the Brother Protocol 2 completion code table.  It has no local imports, so
any sibling module can import from it without risk of circular imports.
"""
import asyncio
import weakref
from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.clients.telnet_client import CNCTelnetClient

# ---------------------------------------------------------------------------
# Per-machine asyncio locks (single-backend deployment)
# ---------------------------------------------------------------------------

_machine_locks: Dict[Tuple[str, int], asyncio.Lock] = {}
_locks_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# Registry of active telnet clients so we can close sockets on reload
# ---------------------------------------------------------------------------

_active_clients: "weakref.WeakSet[CNCTelnetClient]" = weakref.WeakSet()
_active_clients_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# In-memory control version cache: (ip, port) -> (version_str, expiry_time)
# ---------------------------------------------------------------------------

_control_version_cache: Dict[Tuple[str, int], Tuple[str, float]] = {}


# ---------------------------------------------------------------------------
# Per-machine lock helper
# ---------------------------------------------------------------------------

async def _get_machine_lock(ip_address: str, port: int) -> asyncio.Lock:
    """Return (or create) an asyncio.Lock scoped to (ip_address, port).

    Ensures only one telnet operation runs at a time per machine, preventing
    conflicts between the polling loop and API write endpoints.
    """
    key = (ip_address, port)
    async with _locks_lock:
        if key not in _machine_locks:
            _machine_locks[key] = asyncio.Lock()
        return _machine_locks[key]


# ---------------------------------------------------------------------------
# Brother Protocol 2 completion codes (Section 5.5.9.2)
# ---------------------------------------------------------------------------

COMPLETION_CODES = {
    "00": "Normally ended",
    "01": "Invalid data is received",
    "02": "Illegal slave command header",
    "04": "Illegal slave command check sum",
    "05": "Currently in editing or operation mode, or folder in use - cannot delete",
    "06": "Editing error occurred during file operation",
    "07": "The specified data does not exist",
    "08": "Slave command data name is incorrect",
    "09": "The specified data cannot be saved or deleted",
    "10": "Data protection enabled",
    "11": "Remote operation not permitted",
    "13": "Data item is not within allowed range or item count doesn't match",
    "14": "Data version error",
    "15": "During special startup",
    "16": "Cannot read the specified data",
    "17": "Output of drawing data was attempted during drawing",
    "18": "The folder already exists or cannot be deleted",
    "19": "Data size designation is abnormal",
    "20": "Binary data storage error",
    "21": "Auto notification function reserve 1",
    "22": "Auto notification function reserve 2",
    "23": "Access is restricted",
    "30": "Program/data/tool number invalid or out of range",
    "31": "Operation mode conflict or protection enabled",
    "32": "Cannot change during operation or editing",
    "33": "Signal cannot be turned off",
    "34": "Magazine item change without tool number",
    "35": "Pot adjacent to specified pot contains large tool",
    "36": "ATC tool change attempted during memory operation",
    "37": "ATC tool change attempted during MDI operation",
    "38": "Unspecified error during ATC tool change",
    "39": "Unregistered tool registration attempted",
    "40": "Conflict due to communication using other port",
    "41": "Check sum error in specified data",
    "42": "Parity error in specified data",
    "43": "Data too large to store",
    "44": "Cannot store - programs #8000-#8999 are write-protected",
    "45": "Machine unit system is different",
    "46": "Tool unable to change group/main tool/type/color in ATC",
    "60": "Mode change not permitted",
    "61": "Mode change not permitted signal is on",
    "62": "MDI operation mode",
    "63": "During tool change",
    "64": "During automatic centering",
    "65": "During automatic workpiece measurement",
    "66": "Automatic door operation not possible",
    "67": "Operation not possible",
    "68": "No program",
    "69": "Not in memory operation mode",
    "70": "The outer door is open",
    "71": "The door is open",
    "72": "The side door is open",
    "73": "Resetting",
    "74": "Servo control is on",
    "75": "[FEED HOLD] switch is held down",
    "76": "Zero return was not conducted",
    "77": "Restarting program or sequence search in progress",
    "78": "Pallet position error",
    "79": "Performing tool breakage detection",
    "80": "Program number error or different from pallet program",
    "81": "Outer pallet A and B-axes operating",
    "82": "No quick table",
    "83": "[PALLET] key is set to [OFF]",
    "84": "Workpiece counter end",
    "85": "Executing external output command",
    "86": "Memory operation mode",
    "87": "External input not available",
    "88": "In handle mode",
    "89": "XY-axes lock signal is on",
    "90": "Z-axis lock signal is on",
    "91": "*-axis lock signal is on",
    "92": "Pot is not at the top end",
    "93": "Zero return command error",
    "94": "Indexing not permitted signal is on",
    "95": "Pallet start reversed",
    "96": "Outer pallet operating",
    "97": "Communicating",
    "98": "NC or conversation mode is not selected correctly",
    "99": "Reservation",
}
