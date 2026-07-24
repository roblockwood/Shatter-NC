"""API endpoints for notification channel and rule management."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.notification import NotificationChannel, NotificationLog, NotificationRule
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationLogResponse,
    NotificationRuleCreate,
    NotificationRuleResponse,
    NotificationRuleUpdate,
)
from app.utils.secret_redaction import merge_channel_config_update

router = APIRouter()

_notification_service = None


def set_notification_service(service):
    global _notification_service
    _notification_service = service


# --- Channels ---

@router.get("/channels", response_model=list[NotificationChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    return db.query(NotificationChannel).order_by(NotificationChannel.id).all()


@router.post("/channels", response_model=NotificationChannelResponse, status_code=201)
def create_channel(payload: NotificationChannelCreate, db: Session = Depends(get_db)):
    channel = NotificationChannel(**payload.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
def update_channel(channel_id: int, payload: NotificationChannelUpdate, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "config" and value is not None:
            value = merge_channel_config_update(channel.config, value)
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/channels/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()


@router.post("/test/{channel_id}")
async def test_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not _notification_service:
        raise HTTPException(status_code=503, detail="Notification service unavailable")

    status, error = await _notification_service.send_test(channel)
    if status == "sent":
        return {"status": "sent"}
    return {"status": "failed", "error": error}


# --- Rules ---

@router.get("/rules", response_model=list[NotificationRuleResponse])
def list_rules(db: Session = Depends(get_db)):
    return db.query(NotificationRule).order_by(NotificationRule.id).all()


@router.post("/rules", response_model=NotificationRuleResponse, status_code=201)
def create_rule(payload: NotificationRuleCreate, db: Session = Depends(get_db)):
    rule = NotificationRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=NotificationRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
def update_rule(rule_id: int, payload: NotificationRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# --- Delivery Log ---

@router.get("/log", response_model=list[NotificationLogResponse])
def list_log(
    machine_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = min(limit, 200)
    query = db.query(NotificationLog)
    if machine_id is not None:
        query = query.filter(NotificationLog.machine_id == machine_id)
    rows = (
        query.order_by(NotificationLog.sent_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    rule_ids = sorted({r.rule_id for r in rows if r.rule_id is not None})
    rule_name_by_id = {}
    if rule_ids:
        rule_name_by_id = {
            rule.id: rule.name
            for rule in db.query(NotificationRule.id, NotificationRule.name)
            .filter(NotificationRule.id.in_(rule_ids))
            .all()
        }

    for row in rows:
        setattr(row, "rule_name", rule_name_by_id.get(row.rule_id))

    return rows
