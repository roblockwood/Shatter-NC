"""Pydantic schemas for compressor (Kaeser SC2/Connect, backend-direct) API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class CompressorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ip_address: str = Field(..., description="SC2 host (for display / ops)")
    poll_interval_seconds: int = Field(default=1, ge=1, le=300)
    enabled: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    layout_config: Optional[Dict[str, Any]] = Field(default=None)
    kaeser_connect_base_url: Optional[str] = Field(
        None,
        max_length=512,
        description="Kaeser SC2/Connect base URL (e.g. https://192.168.86.101)",
    )
    kaeser_username: Optional[str] = Field(None, max_length=255)


class CompressorCreate(CompressorBase):
    kaeser_password: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def kaeser_all_or_none(self):
        u = (self.kaeser_connect_base_url or "").strip()
        user = (self.kaeser_username or "").strip()
        pw = self.kaeser_password
        has_any = bool(u or user or pw)
        has_all = bool(u and user and pw)
        if has_any and not has_all:
            raise ValueError(
                "Set Kaeser Connect URL, username, and password together, or leave all three blank."
            )
        return self


class CompressorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ip_address: Optional[str] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=1, le=300)
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None
    layout_config: Optional[Dict[str, Any]] = None
    kaeser_connect_base_url: Optional[str] = Field(None, max_length=512)
    kaeser_username: Optional[str] = Field(None, max_length=255)
    kaeser_password: Optional[str] = Field(None, max_length=255)


class CompressorResponse(CompressorBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    kaeser_credentials_configured: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def from_compressor(cls, row: Any) -> "CompressorResponse":
        return cls(
            id=row.id,
            name=row.name,
            ip_address=row.ip_address,
            poll_interval_seconds=row.poll_interval_seconds,
            enabled=row.enabled,
            tags=row.tags or [],
            layout_config=row.layout_config,
            kaeser_connect_base_url=row.kaeser_connect_base_url,
            kaeser_username=row.kaeser_username,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_seen_at=row.last_seen_at,
            kaeser_credentials_configured=bool(
                row.kaeser_password and row.kaeser_username and row.kaeser_connect_base_url
            ),
        )
