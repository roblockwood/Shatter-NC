"""Air compressor configuration (Kaeser SC2/Connect, backend-direct)."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Compressor(Base):
    """Kaeser compressor configured for backend-direct polling."""

    __tablename__ = "compressors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    ip_address = Column(String(45), nullable=False)
    poll_interval_seconds = Column(Integer, nullable=False, default=30)
    enabled = Column(Boolean, nullable=False, default=True)
    tags = Column(JSON, nullable=True)
    layout_config = Column(JSON, nullable=True)

    kaeser_connect_base_url = Column(String(512), nullable=True)
    kaeser_username = Column(String(255), nullable=True)
    kaeser_password = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Compressor(id={self.id}, name='{self.name}', ip='{self.ip_address}')>"
