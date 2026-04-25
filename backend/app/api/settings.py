"""API endpoints for global settings and preferences."""
from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for global layout config (could be moved to database in future)
# For now, we'll use a simple in-memory dict
# In production, this could be stored in a settings table or environment config
_global_layout_config: Dict[str, Any] = {}


@router.get("/layout")
async def get_global_layout():
    """Get global default layout configuration."""
    # Return global layout if set, otherwise return None (frontend will use hardcoded default)
    return {"layout_config": _global_layout_config if _global_layout_config else None}


@router.put("/layout")
async def update_global_layout(layout_config: Dict[str, Any]):
    """Update global default layout configuration."""
    global _global_layout_config
    _global_layout_config = layout_config
    logger.info("Global layout configuration updated")
    return {"layout_config": _global_layout_config}


