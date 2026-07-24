"""Pydantic schemas for notification channel, rule, and log endpoints."""
from datetime import datetime
from typing import Any, Optional
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.utils.secret_redaction import merge_channel_config_update, sanitize_channel_config


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

    @model_validator(mode="before")
    @classmethod
    def sanitize_config(cls, data: Any) -> Any:
        if hasattr(data, "config"):
            return {
                "id": data.id,
                "name": data.name,
                "channel_type": data.channel_type,
                "config": sanitize_channel_config(data.config or {}),
                "enabled": data.enabled,
                "created_at": data.created_at,
            }
        if isinstance(data, dict) and "config" in data:
            sanitized = dict(data)
            sanitized["config"] = sanitize_channel_config(data.get("config") or {})
            return sanitized
        return data


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
