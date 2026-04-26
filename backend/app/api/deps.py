"""Shared FastAPI dependencies and helpers for API routes."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.machine import Machine


def get_machine_or_404(machine_id: int, db: Session) -> Machine:
    """Return the Machine for machine_id or raise HTTPException 404."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=404,
            detail=f"Machine with id {machine_id} not found",
        )
    return machine

