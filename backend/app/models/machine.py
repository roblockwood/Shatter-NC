"""Machine model - stores CNC machine configurations."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Machine(Base):
    """CNC Machine configuration and metadata."""

    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    model = Column(String(100), default="Brother CNC")
    ip_address = Column(String(45), nullable=False)
    ftp_port = Column(Integer, default=21)
    http_port = Column(Integer, default=80)
    ftp_username = Column(String(255), default="anonymous")
    ftp_password = Column(String(255), default="anonymous")
    path = Column(String(255), default="/program")
    tags = Column(JSON, nullable=True)  # ["production", "floor-a"]
    poll_interval_seconds = Column(Integer, default=5)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Machine(id={self.id}, name='{self.name}', ip='{self.ip_address}')>"
