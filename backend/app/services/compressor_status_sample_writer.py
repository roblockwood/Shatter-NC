"""Persist compressor status samples (Timescale) — MQTT and/or poll sources, throttled."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.db.base import SessionLocal
from app.models.event import CompressorStatusSample

logger = logging.getLogger(__name__)

_last_sample_monotonic: Dict[int, float] = {}
_throttle_lock = Lock()


def _min_interval_seconds() -> float:
    from app.core.config import settings

    return max(0.05, float(settings.COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS))


def record_compressor_status_sample(
    compressor_id: int,
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
) -> bool:
    """Insert one sample row. Returns False on failure (missing table, FK, etc.)."""
    db = SessionLocal()
    try:
        row = CompressorStatusSample(
            time=datetime.now(timezone.utc),
            compressor_id=compressor_id,
            status=status or "unknown",
            metrics=metrics,
        )
        db.add(row)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning(
            "Compressor status sample insert failed (compressor_id=%s): %s — "
            "if the table is missing, apply database/init/18-compressor-status-samples.sql "
            "or restart the backend so run_migrations.py can apply pending *.sql files.",
            compressor_id,
            e,
        )
        return False
    finally:
        db.close()


def record_compressor_status_sample_throttled(
    compressor_id: int,
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
    *,
    min_interval_seconds: Optional[float] = None,
) -> bool:
    """
    Insert a sample if min_interval_seconds has passed since the last successful write for this compressor.
    Used by MQTT and poll paths so the timeline fills even when MQTT is disabled or misconfigured.
    """
    iv = min_interval_seconds if min_interval_seconds is not None else _min_interval_seconds()
    with _throttle_lock:
        now = time.monotonic()
        prev_last = _last_sample_monotonic.get(compressor_id, 0.0)
        if now - prev_last < iv:
            return False
        _last_sample_monotonic[compressor_id] = now

    ok = record_compressor_status_sample(compressor_id, status, metrics)
    if not ok:
        with _throttle_lock:
            _last_sample_monotonic[compressor_id] = prev_last
    return ok
