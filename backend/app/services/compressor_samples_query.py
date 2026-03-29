"""Read compressor timeline samples: high-res raw + 1-minute continuous aggregate for older data."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import CompressorStatusSample
from app.schemas.event import CompressorStatusSampleResponse

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cagg_row_to_response(row) -> CompressorStatusSampleResponse:
    m = row._mapping
    return CompressorStatusSampleResponse(
        time=m["time"],
        compressor_id=m["compressor_id"],
        status=m["status"],
        metrics=m["metrics"],
    )


def get_compressor_status_samples_for_charts(
    db: Session,
    compressor_id: int,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    limit: int,
) -> List[CompressorStatusSampleResponse]:
    """
    Newest-first capped sample list, then reversed to chronological order for charts.

    Raw hypertable holds high-resolution rows for COMPRESSOR_STATUS_SAMPLES_RAW_DAYS.
    Older intervals are served from compressor_status_samples_1min (Timescale continuous aggregate).
    """
    now = _utcnow()
    en = end_time or now
    st = start_time or (now - timedelta(days=400))
    cutoff = now - timedelta(days=max(1, settings.COMPRESSOR_STATUS_SAMPLES_RAW_DAYS))

    raw_lo = max(st, cutoff)
    raw_hi = en

    raw_rows: List[CompressorStatusSample] = []
    if raw_lo <= raw_hi:
        raw_rows = (
            db.query(CompressorStatusSample)
            .filter(
                CompressorStatusSample.compressor_id == compressor_id,
                CompressorStatusSample.time >= raw_lo,
                CompressorStatusSample.time <= raw_hi,
            )
            .order_by(desc(CompressorStatusSample.time))
            .limit(limit)
            .all()
        )

    need = limit - len(raw_rows)
    cagg_rows: List = []
    if need > 0 and st < cutoff:
        cagg_hi = min(en, cutoff)
        if st < cagg_hi:
            try:
                sql = text(
                    """
                    SELECT bucket AS time, compressor_id, status, metrics
                    FROM compressor_status_samples_1min
                    WHERE compressor_id = :cid
                      AND bucket >= :st
                      AND bucket < :cagg_hi
                    ORDER BY bucket DESC
                    LIMIT :lim
                    """
                )
                cagg_rows = list(
                    db.execute(
                        sql,
                        {"cid": compressor_id, "st": st, "cagg_hi": cagg_hi, "lim": need},
                    ).fetchall()
                )
            except Exception as e:
                logger.warning(
                    "compressor_status_samples_1min unavailable (%s); using raw rows only",
                    e,
                )

    newest_first: List[CompressorStatusSampleResponse] = [
        CompressorStatusSampleResponse(
            time=r.time,
            compressor_id=r.compressor_id,
            status=r.status,
            metrics=r.metrics,
        )
        for r in raw_rows
    ]
    newest_first.extend(_cagg_row_to_response(r) for r in cagg_rows)

    return list(reversed(newest_first))
