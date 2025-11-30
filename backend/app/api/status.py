"""API endpoints for real-time machine status."""
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.machine import Machine
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{machine_id}/status")
async def get_machine_status(machine_id: int, db: Session = Depends(get_db)):
    """
    Get comprehensive real-time status for a machine.

    Fetches data from HTTP endpoints including:
    - Running log (program, cycle time, etc.)
    - Work counters
    - Alarms
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        http_client = CNCHttpClient(
            db_machine.ip_address,
            port=db_machine.http_port,
            timeout=5,
        )

        # Get comprehensive status
        status_data = http_client.get_status_overview()
        status_data["machine_id"] = machine_id
        status_data["machine_name"] = db_machine.name

        return status_data

    except Exception as e:
        logger.error(f"Error fetching status for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine status: {str(e)}",
        )


@router.get("/{machine_id}/running-log")
async def get_running_log(machine_id: int, db: Session = Depends(get_db)):
    """Get running log data (time display)."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
        data = http_client.get_running_log()
        data["machine_id"] = machine_id
        return data

    except Exception as e:
        logger.error(f"Error fetching running log for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/counters")
async def get_work_counters(machine_id: int, db: Session = Depends(get_db)):
    """Get workpiece counter data."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
        data = http_client.get_work_counter()
        data["machine_id"] = machine_id
        return data

    except Exception as e:
        logger.error(f"Error fetching counters for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/alarms")
async def get_alarms(machine_id: int, db: Session = Depends(get_db)):
    """Get alarm log data."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
        data = http_client.get_alarm_log()
        data["machine_id"] = machine_id
        return data

    except Exception as e:
        logger.error(f"Error fetching alarms for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/tools")
async def get_tools(machine_id: int, db: Session = Depends(get_db)):
    """Get ATC tool data."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        http_client = CNCHttpClient(db_machine.ip_address, port=db_machine.http_port)
        data = http_client.get_tool_data()
        data["machine_id"] = machine_id
        return data

    except Exception as e:
        logger.error(f"Error fetching tools for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/programs")
async def list_programs(machine_id: int, db: Session = Depends(get_db)):
    """List NC programs on machine via FTP."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        programs = await ftp_client.get_programs()
        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "programs": programs,
            "total_count": len(programs),
        }

    except Exception as e:
        logger.error(f"Error listing programs for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/position")
async def get_position(machine_id: int, db: Session = Depends(get_db)):
    """Get current machine position from POSNI1.NC file."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        position_data = await ftp_client.get_position_data()

        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "position_data": position_data,
            "note": "Raw POSNI1.NC data - parsing not yet implemented",
        }

    except Exception as e:
        logger.error(f"Error fetching position for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
