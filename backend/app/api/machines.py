"""API endpoints for machine management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.base import get_db
from app.models.machine import Machine
from app.schemas.machine import MachineCreate, MachineUpdate, MachineResponse
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
from app.utils.protocol_detector import detect_protocols
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Polling service will be injected from main.py
polling_service = None

def set_polling_service(service):
    """Inject the polling service from main.py"""
    global polling_service
    polling_service = service


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

    # Update in-memory poller config (used to populate websocket status fields)
    try:
        if polling_service and machine_id in getattr(polling_service, "pollers", {}):
            poller = polling_service.pollers[machine_id]
            if getattr(poller, "machine", None):
                poller.machine.part_display_mode = getattr(db_machine, "part_display_mode", "parts")
                poller.machine.control_version = getattr(db_machine, "control_version", None)
                poller.machine.units = getattr(db_machine, "units", "in")
    except Exception as e:
        logger.warning(f"Failed to update poller config for machine {machine_id}: {e}")

    # Update websocket cached status so connected dashboards reflect config changes immediately
    try:
        if polling_service and getattr(polling_service, "websocket_manager", None):
            cached = polling_service.websocket_manager.get_machine_status(machine_id) or {}
            merged = {
                **cached,
                "machine_id": machine_id,
                "machine_name": db_machine.name,
                "part_display_mode": getattr(db_machine, "part_display_mode", "parts"),
                "control_version": getattr(db_machine, "control_version", None),
                "units": getattr(db_machine, "units", "in"),
            }
            await polling_service.websocket_manager.broadcast_status(merged)
    except Exception as e:
        logger.warning(f"Failed to broadcast machine config update for machine {machine_id}: {e}")

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
    """Test connection to a machine (Telnet and FTP)."""
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

    # Test Telnet connection (primary communication protocol)
    try:
        from datetime import datetime
        from app.clients.telnet_client import CNCTelnetClient
        telnet_client = CNCTelnetClient(
            db_machine.ip_address,
            port=10000,  # Telnet port is always 10000
            timeout=5,
        )
        # Use LOD MEM (with built-in retry/reconnect in load_data) as health check.
        # This mirrors the same read path used by polling and is more reliable than a
        # single-shot command check under transient contention.
        start_time = datetime.now()
        mem_data = await telnet_client.load_data("MEM", verbose=False, max_retries=2)
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000

        if mem_data:
            results["telnet"] = {
                "success": True,
                "latency_ms": round(latency, 2),
                "status_code": "00",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            results["telnet"] = {
                "success": False,
                "latency_ms": round(latency, 2),
                "status_code": None,
                "timestamp": datetime.now().isoformat(),
            }
        # Clean up test connection
        await telnet_client.disconnect()
    except Exception as e:
        logger.error(f"Telnet test error for machine {machine_id}: {e}")
        results["telnet"] = {"success": False, "error": str(e)}

    # Test FTP connection (for file operations)
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

    # Determine overall status (Telnet is primary, FTP is secondary)
    telnet_ok = results.get("telnet", {}).get("success", False)
    ftp_ok = results.get("ftp", {}).get("success", False)

    if telnet_ok and ftp_ok:
        results["overall_status"] = "online"
    elif telnet_ok:
        results["overall_status"] = "online"  # Telnet is sufficient for data operations
    elif ftp_ok:
        results["overall_status"] = "partial"  # FTP only (can do file ops but not data reads)
    else:
        results["overall_status"] = "offline"

    return results


@router.post("/{machine_id}/detect-protocols")
async def detect_machine_protocols(machine_id: int, db: Session = Depends(get_db)):
    """
    Detect available communication protocols on a machine.
    
    Scans for FOCAS and other control protocols that may be available.
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


@router.get("/{machine_id}/layout")
async def get_machine_layout(machine_id: int, db: Session = Depends(get_db)):
    """Get layout configuration for a specific machine."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    
    # Return layout_config if it exists, otherwise return None (frontend will use default)
    return {"layout_config": machine.layout_config}


@router.put("/{machine_id}/layout")
async def update_machine_layout(
    machine_id: int,
    layout_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update layout configuration for a specific machine."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    
    # Store the entire layout_config dict (which contains panes and optionally gridCols)
    machine.layout_config = layout_config
    db.commit()
    db.refresh(machine)
    
    return {"layout_config": machine.layout_config}


@router.post("/{machine_id}/refresh-program-name")
async def refresh_program_name(machine_id: int, db: Session = Depends(get_db)):
    """
    Manually refresh the active program name from MEM for a machine.
    
    Phase 5: Replace FTP reads - MEM now uses Telnet.
    This fetches the program_name from the machine via Telnet (MEM file)
    and updates the cached value, which will be included in the next status update.
    """
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    
    telnet_client = None
    try:
        from app.clients.telnet_client import create_fresh_connection
        from app.parsers.mem_parser_v2 import parse_mem_v2

        # Create fresh connection
        telnet_client = await create_fresh_connection(
            ip_address=machine.ip_address,
            port=10000,
            timeout=10
        )
        mem_data = await telnet_client.get_memory_data(verbose=False)
        
        if not mem_data:
            # Connection is cleaned up automatically - don't disconnect manually
            return {
                "success": False,
                "message": "MEM file not found or empty via Telnet",
                "program_name": None
            }
        
        logger.debug(f"Machine {machine_id} - Raw MEM content: {repr(mem_data)}")
        parsed_mem = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
        program_name = parsed_mem.get("program_name")
        
        if program_name:
            # Update the cached value in the poller if it exists
            if polling_service and machine_id in polling_service.pollers:
                poller = polling_service.pollers[machine_id]
                poller.cached_program_name = program_name
                poller.program_name_fetched = True
                # Broadcast updated status with new program_name
                status_data = await poller.poll()
                await polling_service.websocket_manager.broadcast_status(status_data)
            
            # Connection is cleaned up automatically - don't disconnect manually
            return {
                "success": True,
                "message": f"Program name refreshed: {program_name}",
                "program_name": program_name
            }
        else:
            # Connection is cleaned up automatically - don't disconnect manually
            return {
                "success": False,
                "message": "MEM parsed but no program_name found",
                "program_name": None,
                "raw_content": mem_data
            }
            
    except Exception as e:
        logger.error(f"Error refreshing program_name for machine {machine_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh program name: {str(e)}",
        )
    finally:
        if telnet_client:
            await telnet_client.disconnect()
