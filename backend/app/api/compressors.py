"""API endpoints for air compressors (Kaeser SC2/Connect, backend-direct)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Dict

from app.db.base import get_db
from app.models.compressor import Compressor
from app.schemas.compressor import CompressorCreate, CompressorUpdate, CompressorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

compressor_polling_service = None
websocket_manager_ref = None


def set_compressor_polling_service(service):
    global compressor_polling_service
    compressor_polling_service = service


def set_websocket_manager_for_compressors(manager):
    global websocket_manager_ref
    websocket_manager_ref = manager


@router.get("/", response_model=List[CompressorResponse])
async def list_compressors(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Compressor)
    if enabled_only:
        q = q.filter(Compressor.enabled)
    rows = q.offset(skip).limit(limit).all()
    return [CompressorResponse.from_compressor(r) for r in rows]


@router.get("/{compressor_id}", response_model=CompressorResponse)
async def get_compressor(compressor_id: int, db: Session = Depends(get_db)):
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    return CompressorResponse.from_compressor(row)


@router.get("/{compressor_id}/status")
async def get_compressor_status(compressor_id: int, db: Session = Depends(get_db)):
    """Latest cached status from compressor polling (same idea as CNC cached status)."""
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    if not websocket_manager_ref:
        return {"compressor_id": compressor_id, "cached": False, "data": {}}
    data = websocket_manager_ref.get_compressor_status(compressor_id)
    return {"compressor_id": compressor_id, "cached": bool(data), "data": data}


@router.post("/", response_model=CompressorResponse, status_code=status.HTTP_201_CREATED)
async def create_compressor(body: CompressorCreate, db: Session = Depends(get_db)):
    existing = db.query(Compressor).filter(Compressor.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Compressor with name '{body.name}' already exists")
    payload = body.model_dump()
    row = Compressor(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return CompressorResponse.from_compressor(row)


@router.put("/{compressor_id}", response_model=CompressorResponse)
async def update_compressor(
    compressor_id: int,
    body: CompressorUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    raw = body.model_dump(exclude_unset=True)
    if "kaeser_password" in raw:
        pw = raw.pop("kaeser_password")
        if pw is None or (isinstance(pw, str) and not pw.strip()):
            row.kaeser_password = None
        else:
            row.kaeser_password = str(pw)
    for k, v in raw.items():
        if k in ("kaeser_connect_base_url", "kaeser_username"):
            if v is None or (isinstance(v, str) and not v.strip()):
                setattr(row, k, None)
            else:
                setattr(row, k, v.strip() if isinstance(v, str) else v)
        else:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)

    if websocket_manager_ref and compressor_polling_service:
        try:
            cached = websocket_manager_ref.get_compressor_status(compressor_id) or {}
            merged: Dict[str, Any] = {
                **cached,
                "asset_kind": "compressor",
                "compressor_id": compressor_id,
                "compressor_name": row.name,
                "ip_address": row.ip_address,
                "enabled": row.enabled,
                "poll_interval_seconds": row.poll_interval_seconds,
                "kaeser_connect_base_url": row.kaeser_connect_base_url,
                "kaeser_username": row.kaeser_username,
                "kaeser_credentials_configured": bool(
                    row.kaeser_password and row.kaeser_username and row.kaeser_connect_base_url
                ),
            }
            await websocket_manager_ref.broadcast_compressor_status(merged)
        except Exception as e:
            logger.warning("Failed to broadcast compressor config update: %s", e)

    return CompressorResponse.from_compressor(row)


@router.get("/{compressor_id}/layout")
async def get_compressor_layout(compressor_id: int, db: Session = Depends(get_db)):
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    return {"layout_config": row.layout_config}


@router.put("/{compressor_id}/layout")
async def update_compressor_layout(
    compressor_id: int,
    layout_config: Dict[str, Any],
    db: Session = Depends(get_db),
):
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    row.layout_config = layout_config
    db.commit()
    db.refresh(row)
    return {"layout_config": row.layout_config}


@router.delete("/{compressor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compressor(compressor_id: int, db: Session = Depends(get_db)):
    row = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compressor not found")
    db.delete(row)
    db.commit()
    if websocket_manager_ref:
        websocket_manager_ref.pop_compressor_cache(compressor_id)
    return None
