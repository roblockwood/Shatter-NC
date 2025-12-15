"""Tool management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.base import get_db
from app.services.tool_service import ToolService
from app.schemas.tools import (
    ToolSummaryResponse,
    ToolDetail,
    ToolHistoryResponse,
    ExportRequest,
    ToolInstancesResponse
)
from app.utils.export_utils import (
    generate_csv,
    generate_json_export,
    flatten_tool_data_for_csv,
    TOOL_EXPORT_CSV_HEADERS
)

router = APIRouter()


@router.get("/summary", response_model=ToolSummaryResponse)
async def get_tool_summary(db: Session = Depends(get_db)):
    """
    Get aggregated summary of all tools across all programs.

    Returns:
        ToolSummaryResponse with list of all tools and summary statistics

    Example:
        GET /api/tools/summary
    """
    try:
        return ToolService.get_tool_summary(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool summary: {str(e)}"
        )


@router.get("/{tool_number}", response_model=ToolDetail)
async def get_tool_detail(
    tool_number: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed analysis for a specific tool.

    Args:
        tool_number: Tool number (1-99)

    Returns:
        ToolDetail with specifications, usage stats, operations, programs, alarms

    Example:
        GET /api/tools/1
    """
    if tool_number < 1 or tool_number > 99:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool number must be between 1 and 99"
        )

    try:
        return ToolService.get_tool_detail(db, tool_number)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool detail: {str(e)}"
        )


@router.get("/{tool_number}/history", response_model=ToolHistoryResponse)
async def get_tool_history(
    tool_number: int,
    start_date: Optional[datetime] = Query(None, description="Filter runs after this date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter runs before this date (ISO 8601)"),
    machine_id: Optional[int] = Query(None, description="Filter by machine ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of runs to return"),
    db: Session = Depends(get_db)
):
    """
    Get production run history for a specific tool.

    Args:
        tool_number: Tool number (1-99)
        start_date: Optional start date filter (ISO 8601 format)
        end_date: Optional end date filter (ISO 8601 format)
        machine_id: Optional machine ID filter
        limit: Maximum number of runs (default 100, max 1000)

    Returns:
        ToolHistoryResponse with list of production runs

    Example:
        GET /api/tools/1/history?start_date=2025-01-01T00:00:00Z&limit=50
    """
    if tool_number < 1 or tool_number > 99:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool number must be between 1 and 99"
        )

    try:
        return ToolService.get_tool_history(
            db=db,
            tool_number=tool_number,
            start_date=start_date,
            end_date=end_date,
            machine_id=machine_id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool history: {str(e)}"
        )


@router.post("/export")
async def export_tool_data(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export tool data in CSV or JSON format.

    Request body:
        - format: "csv" or "json"
        - filters: Optional filters (tool_numbers, start_date, end_date, machine_ids)
        - include_operations: Include operation-level data (default: true)
        - include_programs: Include program usage details (default: false)

    Returns:
        File download with appropriate MIME type

    Example:
        POST /api/tools/export
        {
            "format": "csv",
            "filters": {
                "tool_numbers": [1, 3, 5],
                "start_date": "2025-01-01T00:00:00Z"
            },
            "include_operations": true
        }
    """
    try:
        # Get tool summary
        summary = ToolService.get_tool_summary(db)

        # Apply tool number filter if specified
        tools = summary.tools
        if request.filters and request.filters.tool_numbers:
            tools = [t for t in tools if t.tool_number in request.filters.tool_numbers]

        # Build export data
        if request.format == "csv":
            # Flatten data for CSV
            csv_rows = []

            for tool in tools:
                # Get detailed info for programs with operations if requested
                if request.include_operations or request.include_programs:
                    detail = ToolService.get_tool_detail(db, tool.tool_number)
                    programs = [p.dict() for p in detail.programs]
                else:
                    programs = []

                # Flatten tool data with per-program operations
                flattened = flatten_tool_data_for_csv(
                    tool_number=tool.tool_number,
                    diameter=tool.diameter,
                    description=tool.description,
                    total_runtime_seconds=tool.estimated_runtime_seconds,
                    total_programs=tool.programs_using,
                    total_runs=tool.total_runs,
                    programs=programs
                )

                csv_rows.extend(flattened)

            # Generate CSV
            csv_content = generate_csv(csv_rows, TOOL_EXPORT_CSV_HEADERS)

            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=tools_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )

        elif request.format == "json":
            # Build JSON export
            export_data = {
                "export_date": datetime.now().isoformat(),
                "total_tools": len(tools),
                "filters": request.filters.dict() if request.filters else {},
                "tools": []
            }

            for tool in tools:
                tool_data = tool.dict()

                # Add detailed information if requested
                if request.include_operations or request.include_programs:
                    detail = ToolService.get_tool_detail(db, tool.tool_number)

                    # Programs now contain nested operations, so both flags use programs
                    if request.include_operations or request.include_programs:
                        tool_data["programs"] = [p.dict() for p in detail.programs]

                export_data["tools"].append(tool_data)

            # Generate JSON
            json_content = generate_json_export(export_data)

            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=tools_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export tool data: {str(e)}"
        )


@router.get("/instances/{machine_id}", response_model=ToolInstancesResponse)
async def get_tool_instances(
    machine_id: int,
    db: Session = Depends(get_db)
):
    """
    Get tool instance tracking for a specific machine.

    Note: Tool instance tracking is currently unpopulated. This endpoint provides
    infrastructure for future tool replacement tracking functionality.

    Args:
        machine_id: Machine ID

    Returns:
        ToolInstancesResponse (currently empty with informational note)

    Example:
        GET /api/tools/instances/1
    """
    from app.models.tool_instance import ToolInstance

    instances = db.query(ToolInstance).filter(
        ToolInstance.machine_id == machine_id
    ).all()

    active_count = sum(1 for inst in instances if inst.is_active)

    return ToolInstancesResponse(
        machine_id=machine_id,
        total_instances=len(instances),
        active_instances=active_count,
        instances=[],  # Convert to response schema if instances exist
        note="Tool instance tracking is currently unpopulated. This is infrastructure for future tool replacement tracking."
    )
