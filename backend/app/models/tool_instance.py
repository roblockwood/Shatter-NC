"""Tool instance model - tracks physical tool lifecycle."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ToolInstance(Base):
    """
    Physical tool instance tracking for lifecycle management.

    Tracks individual physical tools installed in machines, enabling:
    - Tool life analysis (runtime between replacements)
    - Replacement history and reasons
    - Cost tracking per tool instance
    - Premature failure detection

    Initially unpopulated - infrastructure for future enhancement.
    """

    __tablename__ = "tool_instances"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_number = Column(Integer, nullable=False)

    # Tool specifications
    diameter = Column(Float, nullable=False)
    corner_radius = Column(Float, default=0.0)
    description = Column(String(500))
    length_total = Column(Float)

    # Lifecycle tracking
    installed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    removed_at = Column(DateTime(timezone=True))
    removal_reason = Column(String(100))
    # removal_reason values: 'normal_wear', 'breakage', 'upgrade', 'scheduled'

    # Usage metrics (aggregated from production runs)
    total_runtime_seconds = Column(Integer, default=0)
    total_parts_produced = Column(Integer, default=0)
    total_cycles = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    machine = relationship("Machine")

    __table_args__ = (
        CheckConstraint('removed_at IS NULL OR removed_at >= installed_at', name='valid_removal_date'),
    )

    def __repr__(self):
        return f"<ToolInstance(id={self.id}, machine_id={self.machine_id}, T{self.tool_number:02d}, active={self.is_active})>"
