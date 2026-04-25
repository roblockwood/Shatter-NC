"""Kaeser SC2/Connect client (backend-direct, no sidecar).

Protocol notes (ported from vendor/kaeser-sc2-api):
- Base URL serves /login.html (session handshake) and /json.json (data RPC).
- Session cookies: Session-Id, Session-Key.
- Session auth: ha1 = sha256(f"{user}:user@sc2:{pass}"), session_auth = sha256(f"{ha1}:{Session-Key}").
- Requests include `Username` + `Session-Auth` + cookies and unit/language preferences.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

SC2_OPERATIONAL_IDS = {
    "POWER_STATE": 4049696,
    "COMPRESSOR_STATE": 4472584,
    "START_MODE": 4057536,
    "PRESSURE": 3489792,
    "OUTLET_TEMP": 3489952,
    "LAST_POWER_DATE": 3200672,
    "LAST_POWER_TIME": 3200752,
    "PANEL_CLOCK": 3489872,
    "KEY_LABEL": 4446952,
    "KEY_TOGGLE": 4430360,
    "KEY_CODE": 4419664,
    "KEY_RIGHT": 4406224,
    "RUN_HOURS_DISPLAY": 4361464,
    "LOAD_HOURS_DISPLAY": 4348032,
    "MAINTENANCE_HOURS_DISPLAY": 4301592,
}


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _normalize_base_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        # Kaeser Connect is typically https.
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return raw.rstrip("/")


_UNIT_COOKIE = (
    "Unit_Time=2; Unit_Date=2; Unit_VolBufferVolume=2; Unit_VolDeliveryQuantity=1; "
    "Unit_DeliveryQuantity=1; Unit_Temperature=2; Unit_Pressure=3; Language=en_US; "
    "AccessRights=1; AccessLevel=2;"
)


@dataclass
class KaeserSession:
    session_id: str = ""
    session_key: str = ""
    session_auth: str = ""
    active: bool = False


class KaeserSc2Client:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        verify_tls: bool = False,
    ):
        self.base_url = _normalize_base_url(base_url)
        self.username = (username or "").strip()
        self.password = password or ""
        self.verify_tls = verify_tls
        self._ha1 = _sha256_hex(f"{self.username}:user@sc2:{self.password}") if self.username else ""
        self._session = KaeserSession()
        self._http: Optional[httpx.AsyncClient] = None

    async def aclose(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    def _client(self) -> httpx.AsyncClient:
        if not self._http:
            self._http = httpx.AsyncClient(verify=self.verify_tls, timeout=httpx.Timeout(45.0))
        return self._http

    def _base_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Username": self.username,
        }

    def _cookie_header(self, session_id: Optional[str] = None, session_key: Optional[str] = None) -> str:
        sid = session_id if session_id is not None else self._session.session_id
        sk = session_key if session_key is not None else self._session.session_key
        parts = []
        if sid:
            parts.append(f"Session-Id={sid};")
        if sk:
            parts.append(f"Session-Key={sk};")
        parts.append(_UNIT_COOKIE)
        return " ".join(parts).strip()

    def _session_auth_for_key(self, session_key: str) -> str:
        if not self._ha1 or not session_key:
            return ""
        return _sha256_hex(f"{self._ha1}:{session_key}")

    @staticmethod
    def _extract_set_cookie(headers: httpx.Headers) -> Tuple[str, str]:
        # httpx normalizes Set-Cookie into get_list
        cookies = headers.get_list("set-cookie")
        sid = ""
        sk = ""
        for c in cookies:
            if c.startswith("Session-Id="):
                sid = c.split(";", 1)[0].split("=", 1)[1]
            if c.startswith("Session-Key="):
                sk = c.split(";", 1)[0].split("=", 1)[1]
        return sid, sk

    async def _refresh_session(self) -> None:
        if not (self.base_url and self.username and self.password):
            self._session = KaeserSession(active=False)
            raise ValueError("Kaeser SC2 credentials not configured")

        client = self._client()
        # Ported from sidecar: start with empty cookie and retry to get active session.
        sid = ""
        sk = ""
        for _ in range(10):
            s_auth = self._session_auth_for_key(sk)
            headers = {
                **self._base_headers(),
                "Session-Auth": s_auth,
                "Cookie": self._cookie_header(session_id=sid, session_key=sk),
            }
            try:
                r = await client.get(f"{self.base_url}/login.html", headers=headers)
            except Exception:
                self._session = KaeserSession(active=False)
                raise

            new_sid, new_sk = self._extract_set_cookie(r.headers)
            # Sidecar treats sessionId length > 1 as active, with special -1 over-limit case.
            if new_sid == "-1":
                raise RuntimeError("Kaeser SC2 over session limit (Session-Id=-1)")
            if new_sid and len(new_sid) > 1:
                sid, sk = new_sid, new_sk
                self._session = KaeserSession(
                    session_id=sid,
                    session_key=sk,
                    session_auth=self._session_auth_for_key(sk),
                    active=True,
                )
                return
            sid, sk = new_sid, new_sk

        self._session = KaeserSession(active=False)
        raise RuntimeError("Kaeser SC2 session refresh failed")

    async def _request_json(self, payload: Dict[str, Any]) -> Any:
        client = self._client()

        if not self._session.active:
            await self._refresh_session()

        headers = {
            **self._base_headers(),
            "Session-Auth": self._session.session_auth,
            "Cookie": self._cookie_header(),
        }
        r = await client.post(f"{self.base_url}/json.json", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        # Sidecar heuristic: invalid session returns empty/incorrect payload at index '2'.
        try:
            payload_check = data.get("2") if isinstance(data, dict) else None
        except Exception:
            payload_check = None
        if payload_check in ("", "Incorrect JSON format received."):
            # attempt refresh and retry once
            await self._refresh_session()
            headers["Session-Auth"] = self._session.session_auth
            headers["Cookie"] = self._cookie_header()
            r2 = await client.post(f"{self.base_url}/json.json", headers=headers, json=payload)
            r2.raise_for_status()
            return r2.json()
        return data

    @staticmethod
    def _block3_items(data: Any) -> Dict[str, Any]:
        block = data.get("3") if isinstance(data, dict) else None
        return block if isinstance(block, dict) else {}

    @staticmethod
    def _id_matches(item_id: Any, wanted: int) -> bool:
        if item_id == wanted:
            return True
        if isinstance(item_id, str):
            try:
                return int(item_id) == wanted
            except ValueError:
                return False
        return False

    @staticmethod
    def _coerce_str(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, (int, float, bool)):
            return str(v)
        return ""

    @staticmethod
    def _coerce_num(v: Any) -> Optional[float]:
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except ValueError:
                return None
        return None

    def _extract_value_item(self, data: Any, wanted_id: int) -> Optional[Dict[str, Any]]:
        for _, item in self._block3_items(data).items():
            if not isinstance(item, dict):
                continue
            if self._id_matches(item.get("Id"), wanted_id):
                return item
        return None

    def _extract_string_value(self, data: Any, wanted_id: int) -> str:
        item = self._extract_value_item(data, wanted_id)
        return self._coerce_str(item.get("Value") if item else None)

    def _extract_numeric_value(self, data: Any, wanted_id: int) -> float:
        item = self._extract_value_item(data, wanted_id)
        n = self._coerce_num(item.get("Value") if item else None)
        return float(n) if n is not None else 0.0

    def _extract_unit(self, data: Any, wanted_id: int) -> str:
        item = self._extract_value_item(data, wanted_id)
        u = item.get("Unit") if item else None
        return u.strip() if isinstance(u, str) and u.strip() else ""

    def _parse_operational(self, raw: Any) -> Dict[str, Any]:
        power_state = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["POWER_STATE"]).strip().lower()

        status_display_raw = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["COMPRESSOR_STATE"]).strip()
        system_status_display = status_display_raw
        cs_raw = status_display_raw.lower()
        if "on load" in cs_raw:
            compressor_state = "load"
        elif "back pressure" in cs_raw:
            compressor_state = "back pressure"
        else:
            compressor_state = cs_raw

        start_mode_raw = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["START_MODE"]).strip().lower()
        start_mode = "remote" if start_mode_raw == "rc" else start_mode_raw

        pressure = self._extract_numeric_value(raw, SC2_OPERATIONAL_IDS["PRESSURE"])
        pressure_unit = self._extract_unit(raw, SC2_OPERATIONAL_IDS["PRESSURE"])
        outlet_temp = self._extract_numeric_value(raw, SC2_OPERATIONAL_IDS["OUTLET_TEMP"])
        outlet_temp_unit = self._extract_unit(raw, SC2_OPERATIONAL_IDS["OUTLET_TEMP"])

        last_power_date = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["LAST_POWER_DATE"])
        last_power_time = (
            self._extract_string_value(raw, SC2_OPERATIONAL_IDS["LAST_POWER_TIME"])
            .replace("AM", "")
            .replace("PM", "")
            .strip()
        )
        last_power_change = f"{last_power_date} {last_power_time}".strip()

        panel_clock = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["PANEL_CLOCK"]).strip()
        key_label = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["KEY_LABEL"]).strip()
        key_toggle = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["KEY_TOGGLE"]).strip()
        key_code = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["KEY_CODE"]).strip()
        key_right = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["KEY_RIGHT"]).strip()
        run_hours_display = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["RUN_HOURS_DISPLAY"]).strip()
        load_hours_display = self._extract_string_value(raw, SC2_OPERATIONAL_IDS["LOAD_HOURS_DISPLAY"]).strip()
        maintenance_hours_display = self._extract_string_value(
            raw, SC2_OPERATIONAL_IDS["MAINTENANCE_HOURS_DISPLAY"]
        ).strip()

        return {
            "powerState": power_state,
            "compressorState": compressor_state,
            "startMode": start_mode,
            "pressure": {"value": pressure, "unit": pressure_unit},
            "inletTemp": {"value": 0, "unit": ""},
            "outletTemp": {"value": outlet_temp, "unit": outlet_temp_unit},
            "motorTemp": {"value": 0, "unit": ""},
            "lastPowerChange": last_power_change,
            "sigmaPanel": {
                "panelClock": panel_clock,
                "systemStatusDisplay": system_status_display,
                "keyLabel": key_label,
                "keyToggle": key_toggle,
                "keyCode": key_code,
                "keyRight": key_right,
                "runHoursDisplay": run_hours_display,
                "loadHoursDisplay": load_hours_display,
                "maintenanceHoursDisplay": maintenance_hours_display,
            },
        }

    def _parse_messages(self, raw: Any) -> Any:
        items = self._block3_items(raw)
        out = []
        for _, m in items.items():
            if not isinstance(m, dict):
                continue
            report_type = self._coerce_str(m.get("ReportTypeTxt")).replace("message", "").strip()
            dt = self._coerce_str(m.get("ReportDateTime")).replace("AM", "").replace("PM", "").strip()
            mid = m.get("ReportId")
            text = self._coerce_str(m.get("Text")).replace("\n", "").strip()
            out.append(
                {
                    "messageType": report_type,
                    "messageId": int(mid) if isinstance(mid, (int, float)) else mid,
                    "messageDate": dt,
                    "message": text,
                }
            )
        return out

    def _parse_operating_hours(self, raw: Any) -> Dict[str, Any]:
        def h(id_: int) -> int:
            for _, item in self._block3_items(raw).items():
                if not isinstance(item, dict):
                    continue
                if item.get("Id") == id_ and isinstance(item.get("Value"), str):
                    try:
                        return int(item["Value"].replace("h", "").strip())
                    except ValueError:
                        return 0
            return 0

        return {
            "compressorHours": h(3261336),
            "onLoadHours": h(3261648),
            "motorHours": h(3261960),
            "compressorBlockHours": h(3262272),
            "sigmaControlHours": h(3262584),
        }

    def _parse_maintenance_timers(self, raw: Any) -> Dict[str, Any]:
        def h(id_: int) -> int:
            for _, item in self._block3_items(raw).items():
                if not isinstance(item, dict):
                    continue
                if item.get("Id") == id_ and isinstance(item.get("Value"), str):
                    try:
                        return int(item["Value"].replace("h", "").strip())
                    except ValueError:
                        return 0
            return 0

        return {
            "oilFilter": {"dueIn": h(3274264), "interval": h(3274104)},
            "oilSeperator": {"dueIn": h(3275288), "interval": h(3275128)},
            "oilChange": {"dueIn": h(3276312), "interval": h(3276152)},
            "airFilter": {"dueIn": h(3277336), "interval": h(3277176)},
            "valveInspection": {"dueIn": h(3278360), "interval": h(3278200)},
            "beltCoupling": {"dueIn": h(3279384), "interval": h(3279224)},
            "compMotorBearingLube": {"dueIn": h(3280640), "interval": h(3280480)},
            "bearingChange": {"dueIn": h(3281432), "interval": h(3281272)},
            "fanMotorBearing": {"dueIn": h(3283480), "interval": h(3283320)},
        }

    def _parse_led_data(self, raw: Any) -> Dict[str, Any]:
        b3 = self._block3_items(raw)
        # Sidecar emitted nested { "led-data": { load, idle, ... } } sometimes.
        # We'll standardize to that shape.
        def is_on(key: str) -> bool:
            it = b3.get(key)
            if not isinstance(it, dict):
                return False
            return it.get("State") == 1

        return {
            "led-data": {
                "powerOn": is_on("led_power_on"),
                "idle": is_on("led_idle"),
                "load": is_on("led_load"),
                "error": is_on("led_error"),
                "errorVoltage": is_on("led_voltage"),
                "comError": is_on("led_com_error"),
                "maintenanceDue": is_on("led_maintenance"),
                "remoteEnabled": is_on("led_remote"),
                "clockEnabled": is_on("led_clock"),
            }
        }

    async def fetch_operational(self) -> Dict[str, Any]:
        payload = {
            "0": 1,
            "1": 2,
            "2": {
                "0": [
                    4049696,
                    4057536,
                    3489792,
                    3489952,
                    4472584,
                    3200672,
                    3200752,
                    3489872,
                    4446952,
                    4430360,
                    4419664,
                    4406224,
                    4361464,
                    4348032,
                    4301592,
                ]
            },
        }
        raw = await self._request_json(payload)
        return raw

    async def fetch_operating_hours(self) -> Dict[str, Any]:
        payload = {"0": 1, "1": 2, "2": {"0": [3261336, 3261648, 3261960, 3262272, 3262584]}}
        return await self._request_json(payload)

    async def fetch_maintenance_timers(self) -> Dict[str, Any]:
        payload = {
            "0": 1,
            "1": 2,
            "2": {
                "0": [
                    3273872,
                    3274104,
                    3274184,
                    3274264,
                    3274896,
                    3275128,
                    3275208,
                    3275288,
                    3275920,
                    3276152,
                    3276232,
                    3276312,
                    3276944,
                    3277176,
                    3277256,
                    3277336,
                    3277968,
                    3278200,
                    3278280,
                    3278360,
                    3278992,
                    3279224,
                    3279304,
                    3279384,
                    3279784,
                    3280016,
                    3280248,
                    3280480,
                    3280560,
                    3280640,
                    3281040,
                    3281272,
                    3281352,
                    3281432,
                    3282064,
                    3283088,
                    3283320,
                    3283400,
                    3283480,
                    3284112,
                    3284344,
                    3284424,
                    3284504,
                    3285136,
                    3285368,
                ]
            },
        }
        return await self._request_json(payload)

    async def fetch_messages(self) -> Dict[str, Any]:
        payload = {"0": 3, "1": 1, "2": {"0": 0, "1": 0, "2": 101}}
        return await self._request_json(payload)

    async def fetch_led_data(self) -> Dict[str, Any]:
        payload = {"0": 1, "1": 4}
        return await self._request_json(payload)

    async def fetch_bundle(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Return (bundle, error). Bundle keys match previous sidecar REST bundle shape."""
        try:
            operational = self._parse_operational(await self.fetch_operational())
            maint = self._parse_maintenance_timers(await self.fetch_maintenance_timers())
            messages = self._parse_messages(await self.fetch_messages())
            hours = self._parse_operating_hours(await self.fetch_operating_hours())
            led_raw = self._parse_led_data(await self.fetch_led_data())

            return (
                {
                    "operational": operational,
                    "maintence": maint,
                    "messages": messages,
                    "operatingHours": hours,
                    "led_data": led_raw,
                },
                None,
            )
        except Exception as e:
            return None, str(e)

