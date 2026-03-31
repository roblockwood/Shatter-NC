"""Write kaeser-sc2-api env files from compressor rows (Nest reads config/kaeser_sc2.env or env at process start)."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.compressor import Compressor

logger = logging.getLogger(__name__)


def _env_value(val: str) -> str:
    """Dotenv-friendly quoting for values with spaces or shell-special characters."""
    if val == "":
        return '""'
    if re.search(r'[\s#"\'\\$`]', val):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return val


def sidecar_env_path(compressor_id: int) -> Optional[Path]:
    base = settings.KAESER_SIDECAR_ENV_DIR
    if not base:
        return None
    return Path(base) / f"compressor-{compressor_id}.env"


def write_compressor_sidecar_env(compressor: "Compressor") -> None:
    """Write compressor-{id}.env for docker env_file. Sidecar must be restarted to pick up changes."""
    path = sidecar_env_path(compressor.id)
    if path is None:
        return

    addr = (compressor.kaeser_connect_base_url or "").strip()
    user = (compressor.kaeser_username or "").strip()
    password = compressor.kaeser_password or ""

    if not (addr and user and password):
        remove_compressor_sidecar_env(compressor.id)
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    mqtt_host = settings.MQTT_BROKER_HOST or "mqtt"
    mqtt_port = str(settings.MQTT_BROKER_PORT)
    mqtt_user = settings.MQTT_USER or ""
    mqtt_pass = settings.MQTT_PASSWORD or ""

    lines = [
        f"KAESER_ADDRESS={_env_value(addr)}",
        f"KAESER_USERNAME={_env_value(user)}",
        f"KAESER_PASSWORD={_env_value(password)}",
        f"MQTT_HOST={_env_value(mqtt_host)}",
        f"MQTT_PORT={mqtt_port}",
        f"MQTT_USER={_env_value(mqtt_user)}",
        f"MQTT_PASS={_env_value(mqtt_pass)}",
        f"MQTT_TOPIC_ROOT={_env_value((compressor.mqtt_topic_root or '').strip())}",
        "LOG_LEVEL=info",
    ]
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    logger.info("Wrote Kaeser sidecar env file %s", path)


def remove_compressor_sidecar_env(compressor_id: int) -> None:
    path = sidecar_env_path(compressor_id)
    if path is None:
        return
    try:
        if path.is_file():
            path.unlink()
            logger.info("Removed Kaeser sidecar env file %s", path)
    except OSError as e:
        logger.warning("Could not remove sidecar env %s: %s", path, e)
