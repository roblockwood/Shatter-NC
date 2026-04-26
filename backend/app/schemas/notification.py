"""Pydantic schemas for notification channel, rule, and log endpoints."""
from datetime import datetime
from typing import Any, Optional
from typing import Literal

from pydantic import BaseModel, Field


class NotificationChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    channel_type: Literal["email", "sms"] = "email"
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    channel_type: Optional[Literal["email", "sms"]] = None
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    machine_id: Optional[int] = None
    trigger_type: Literal["status_change"] = "status_change"
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    channel_ids: list[int] = Field(default_factory=list)
    enabled: bool = True


class NotificationRuleCreate(NotificationRuleBase):
    pass


class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    machine_id: Optional[int] = None
    trigger_type: Optional[Literal["status_change"]] = None
    trigger_config: Optional[dict[str, Any]] = None
    channel_ids: Optional[list[int]] = None
    enabled: Optional[bool] = None


class NotificationRuleResponse(NotificationRuleBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: int
    rule_id: Optional[int]
    rule_name: Optional[str] = None
    channel_id: Optional[int]
    machine_id: Optional[int]
    event_type: str
    event_data: Optional[dict[str, Any]]
    message: Optional[str]
    status: str
    error_message: Optional[str]
    sent_at: datetime

    model_config = {"from_attributes": True}
