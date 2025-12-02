"""API endpoints for real-time machine status."""
from fastapi import APIRouter, Depends, HTTPException, status as http_status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.machine import Machine
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient
from app.parsers.gcode_parser import parse_gcode
import logging
import io

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
async def list_programs(
    machine_id: int,
    path: str = "/",
    db: Session = Depends(get_db)
):
    """
    List files and directories on machine via FTP with navigation support.

    Args:
        machine_id: Machine ID
        path: Directory path to list (default: /)
    """
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
        programs = await ftp_client.get_programs(path)
        return {
            "machine_id": machine_id,
            "machine_name": db_machine.name,
            "current_path": path,
            "programs": programs,
            "total_count": len(programs),
        }

    except Exception as e:
        logger.error(f"Error listing programs for machine {machine_id} at path {path}: {e}")
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


@router.get("/{machine_id}/download")
async def download_file(
    machine_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """
    Download a file from the machine via FTP.

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine (e.g., /O2000.NC)
    """
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
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to download file: {file_path}",
            )

        filename = file_path.split('/')[-1]

        return StreamingResponse(
            iter([file_content]),
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/metadata")
async def get_file_metadata(
    machine_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """
    Get file metadata including tools and runtime estimates.

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine
    """
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
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to read file: {file_path}",
            )

        try:
            text_content = file_content.decode('utf-8', errors='replace')
        except Exception:
            text_content = str(file_content)

        # Parse using the comprehensive G-code parser
        parsed = parse_gcode(text_content)

        # Extract tool numbers from parsed tool data
        tools = [tool["tool_number"] for tool in parsed.get("tools", [])]

        return {
            "file_path": file_path,
            "tools": tools,
            "runtime_seconds": int(parsed.get("estimated_runtime_seconds", 0)),
            "has_errors": False,  # G-code parser doesn't detect errors, but that's OK for display
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file metadata from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{machine_id}/view")
async def view_file(
    machine_id: int,
    file_path: str,
    max_size: int = 8388608,
    db: Session = Depends(get_db)
):
    """
    View file content as text (up to 8MB by default).

    Args:
        machine_id: Machine ID
        file_path: Path to file on machine
        max_size: Maximum file size in bytes (default 8MB)
    """
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
        file_content = await ftp_client.download_file(file_path)

        if file_content is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Failed to read file: {file_path}",
            )

        if len(file_content) > max_size:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_size} bytes",
            )

        try:
            text_content = file_content.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Error decoding file {file_path}: {e}")
            text_content = str(file_content)

        return {
            "file_path": file_path,
            "content": text_content,
            "size": len(file_content),
            "lines": len(text_content.split('\n')),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing file from machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{machine_id}/upload")
async def upload_file(
    machine_id: int,
    file_path: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a file to the machine via FTP.

    Args:
        machine_id: Machine ID
        file_path: Destination path on machine (e.g., /O2000.NC)
        file: File to upload
    """
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )

    try:
        # Read file content
        file_content = await file.read()

        ftp_client = CNCFtpClient(
            db_machine.ip_address,
            port=db_machine.ftp_port,
            username=db_machine.ftp_username,
            password=db_machine.ftp_password,
        )

        result = await ftp_client.upload_file(file_content, file_path)

        if not result.get("success"):
            raise Exception(result.get("error", "Upload failed"))

        return {
            "success": True,
            "file_path": file_path,
            "size": len(file_content),
            "message": f"File uploaded successfully to {file_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to machine {machine_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
