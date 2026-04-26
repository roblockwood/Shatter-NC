"""Notification channel, rule, and delivery log models."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationChannel(Base):
    """Configuration for a notification delivery channel (e.g. email/SMTP)."""

    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(20), nullable=False, default="email")
    config = Column(JSONB, nullable=False, default={})
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationRule(Base):
    """Rule that defines when and where to send notifications."""

    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=True, index=True)
    trigger_type = Column(String(30), nullable=False, default="status_change")
    trigger_config = Column(JSONB, nullable=False, default={})
    channel_ids = Column(ARRAY(Integer), nullable=False, default=[])
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationLog(Base):
    """Record of a notification delivery attempt."""

    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("notification_rules.id", ondelete="SET NULL"), nullable=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="SET NULL"), nullable=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(30), nullable=False)
    event_data = Column(JSONB, nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
