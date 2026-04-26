"""ATC pot optimizer route.

Routes:
    POST /analyze-atc — recommend optimised ATC pot assignments for an NC program
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter()


class ATCOptimizeRequest(BaseModel):
    """Request body for the ATC pot optimizer."""

    gcode_content: str
    num_pockets: int = 21
    current_assignment: Dict[str, int] = {}  # str(tool_number) → current_pot (actual ATC data)
    pinned_tools: List[int] = []  # tool numbers to keep in their current pots


class ATCAssignmentEntry(BaseModel):
    """Recommended or baseline pot for a single tool."""

    tool_number: int
    pot: int


class ATCOptimizeResponse(BaseModel):
    """Optimised ATC pot assignments derived from an NC program."""

    tool_sequence: List[int]
    unique_tools: List[int]
    tool_change_count: int
    transition_matrix: Dict[str, int]
    baseline_assignment: Dict[str, int]
    optimized_assignment: Dict[str, int]
    baseline_cost: int
    optimized_cost: int
    improvement_pct: float


@router.post("/analyze-atc", response_model=ATCOptimizeResponse)
async def analyze_atc_pot_assignment(request: ATCOptimizeRequest):
    """Recommend optimised ATC pot assignments for a Brother NC program.

    Parses the NC content for tool-change calls (G100 / M6 with T-word),
    then runs a simulated-annealing + 2-opt optimiser to find the pot
    placement that minimises total carousel rotation distance.

    The Brother ATC is a rotary magazine: pocket N is physically adjacent to
    pocket 1, so shortest-path travel is ``min(|p1-p2|, N-|p1-p2|)`` steps.

    Args:
        request.gcode_content: Full NC program text.
        request.num_pockets:   Total pockets on the carousel (default 21).

    Returns:
        ATCOptimizeResponse with baseline vs optimised assignments and the
        percentage reduction in total carousel travel distance.
    """

    from app.parsers.nc_tool_sequence_parser import extract_tool_sequence
    from app.services.atc_optimizer import optimize_atc

    if request.num_pockets < 1 or request.num_pockets > 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="num_pockets must be between 1 and 60",
        )

    tool_sequence = extract_tool_sequence(request.gcode_content)

    if not tool_sequence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No tool-change calls found in the NC program. "
                "Expected G100 T## or M6 T## patterns."
            ),
        )

    try:
        current_assignment = {int(k): v for k, v in request.current_assignment.items()} or None
        pinned_map = {t: current_assignment[t] for t in request.pinned_tools if current_assignment and t in current_assignment} or None
        result = optimize_atc(
            tool_sequence=tool_sequence,
            num_pockets=request.num_pockets,
            current_assignment=current_assignment,
            pinned_tools=pinned_map,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Frontend expects tool-number keys without a "T" prefix.
    return ATCOptimizeResponse(
        tool_sequence=result["tool_sequence"],
        unique_tools=result["unique_tools"],
        tool_change_count=result["tool_change_count"],
        transition_matrix=result["transition_matrix"],
        baseline_assignment={k.lstrip("T"): v for k, v in result["baseline_assignment"].items()},
        optimized_assignment={k.lstrip("T"): v for k, v in result["optimized_assignment"].items()},
        baseline_cost=result["baseline_cost"],
        optimized_cost=result["optimized_cost"],
        improvement_pct=result["improvement_pct"],
    )

