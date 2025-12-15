"""API endpoints for machine management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.machine import Machine
from app.schemas.machine import MachineCreate, MachineUpdate, MachineResponse
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
from app.utils.protocol_detector import detect_protocols
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[MachineResponse])
async def list_machines(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    """List all configured machines."""
    query = db.query(Machine)
    if enabled_only:
        query = query.filter(Machine.enabled == True)
    machines = query.offset(skip).limit(limit).all()
    return machines


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(machine_id: int, db: Session = Depends(get_db)):
    """Get a specific machine by ID."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    return machine


@router.post("/", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(machine: MachineCreate, db: Session = Depends(get_db)):
    """Create a new machine configuration."""
    # Check if machine with same name already exists
    existing = db.query(Machine).filter(Machine.name == machine.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with name '{machine.name}' already exists",
        )

    # Create new machine
    db_machine = Machine(**machine.model_dump())
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine


@router.put("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: int, machine_update: MachineUpdate, db: Session = Depends(get_db)
):
    """Update a machine configuration."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    # Update fields
    update_data = machine_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_machine, field, value)

    db.commit()
    db.refresh(db_machine)
    return db_machine


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    """Delete a machine configuration."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    db.delete(db_machine)
    db.commit()
    return None


@router.post("/{machine_id}/test")
async def test_connection(machine_id: int, db: Session = Depends(get_db)):
    """Test connection to a machine (HTTP and FTP)."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    results = {
        "machine_id": machine_id,
        "machine_name": db_machine.name,
        "ip_address": db_machine.ip_address,
    }

    # Test HTTP connection
    try:
        http_client = CNCHttpClient(
            db_machine.ip_address,
            port=db_machine.http_port,
            timeout=5,
        )
        results["http"] = http_client.test_connection()
    except Exception as e:
        logger.error(f"HTTP test error for machine {machine_id}: {e}")
        results["http"] = {"success": False, "error": str(e)}

    # Test FTP connection
    try:
        ftp_client = CNCFtpClient(
            db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
            timeout=5,
        )
        results["ftp"] = await ftp_client.test_connection()
    except Exception as e:
        logger.error(f"FTP test error for machine {machine_id}: {e}")
        results["ftp"] = {"success": False, "error": str(e)}

    # Determine overall status
    http_ok = results.get("http", {}).get("success", False)
    ftp_ok = results.get("ftp", {}).get("success", False)

    if http_ok and ftp_ok:
        results["overall_status"] = "online"
    elif http_ok or ftp_ok:
        results["overall_status"] = "partial"
    else:
        results["overall_status"] = "offline"

    return results


@router.post("/{machine_id}/detect-protocols")
async def detect_machine_protocols(machine_id: int, db: Session = Depends(get_db)):
    """
    Detect available communication protocols on a machine.
    
    Scans for FOCAS, MTConnect, and other control protocols that may be available.
    This can help identify additional functionality beyond HTTP/FTP.
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        # Initialize clients for protocol detection
        http_client = None
        ftp_client = None

        try:
            http_client = CNCHttpClient(
                db_machine.ip_address,
                port=db_machine.http_port,
                timeout=5,
            )
        except Exception as e:
            logger.warning(f"Could not initialize HTTP client: {e}")

        try:
            ftp_client = CNCFtpClient(
                ip_address=db_machine.ip_address,
                port=db_machine.ftp_port,
                username=db_machine.ftp_username,
                password=db_machine.ftp_password,
                timeout=5,
            )
        except Exception as e:
            logger.warning(f"Could not initialize FTP client: {e}")

        # Run protocol detection
        results = await detect_protocols(
            ip_address=db_machine.ip_address,
            http_port=db_machine.http_port,
            ftp_client=ftp_client,
            http_client=http_client,
        )

        # Add machine info to results
        results["machine_id"] = machine_id
        results["machine_name"] = db_machine.name

        return results

    except Exception as e:
        logger.error(f"Protocol detection error for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Protocol detection failed: {str(e)}",
        )


@router.post("/{machine_id}/disconnect")
async def disconnect_machine(machine_id: int, db: Session = Depends(get_db)):
    """Disconnect FTP connection for a machine."""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        ftp_client = CNCFtpClient(
            db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )
        ftp_client.disconnect()
        return {
            "status": "success",
            "message": f"Disconnected from {db_machine.name} ({db_machine.ip_address})",
        }
    except Exception as e:
        logger.error(f"Error disconnecting machine {machine_id}: {e}")
        return {
            "status": "success",
            "message": f"Closed FTP connection attempt (may not have been connected)",
        }


@router.get("/overview")
async def get_machines_overview(db: Session = Depends(get_db)):
    """Get overview status of all machines."""
    machines = db.query(Machine).filter(Machine.enabled == True).all()

    # TODO: Fetch real-time status for each machine
    # For now, return basic info
    overview = []
    for machine in machines:
        overview.append(
            {
                "id": machine.id,
                "name": machine.name,
                "last_seen_at": machine.last_seen_at,
                # "current_program": None,  # TODO: fetch from polling service
                # "current_status": None,   # TODO: fetch from polling service
            }
        )

    return {"total_machines": len(machines), "machines": overview}
