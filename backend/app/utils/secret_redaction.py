"""Helpers for redacting secrets in API responses and merging partial updates."""
from __future__ import annotations

from typing import Any

SECRET_CONFIG_KEYS = frozenset(
    {
        "password",
        "auth_token",
        "api_key",
        "secret",
        "token",
        "smtp_password",
    }
)

MASKED_SECRET = "********"


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in SECRET_CONFIG_KEYS
        or lowered.endswith("_password")
        or lowered.endswith("_token")
        or lowered.endswith("_secret")
    )


def sanitize_channel_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy of channel config with secret values masked for API responses."""
    if not config:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in config.items():
        if _is_secret_key(key) and value:
            sanitized[key] = MASKED_SECRET
        else:
            sanitized[key] = value
    return sanitized


def merge_channel_config_update(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge channel config updates without overwriting secrets when omitted or masked."""
    base = dict(existing or {})
    if not incoming:
        return base
    merged = {**base, **incoming}
    for key, value in incoming.items():
        if _is_secret_key(key) and (not value or value == MASKED_SECRET):
            if key in base:
                merged[key] = base[key]
            else:
                merged.pop(key, None)
    return merged
