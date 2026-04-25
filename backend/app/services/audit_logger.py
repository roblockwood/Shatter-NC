"""
Audit Logging Service for Tool Modifications

Logs all tool modification operations for audit trail and debugging.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for tool modifications."""
    
    @staticmethod
    def log_tool_modification(
        machine_id: int,
        operation_type: str,
        operation_details: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None,
        machine_state: Optional[Dict[str, Any]] = None
    ):
        """
        Log a tool modification operation.
        
        Args:
            machine_id: Machine ID
            operation_type: Type of operation (e.g., 'tool_color', 'tool_assignment')
            operation_details: Dict with operation-specific details:
                - For color: pot_number, tool_number, old_color, new_color
                - For assignment: pot_number, old_tool_number, new_tool_number
                - For type: pot_number, tool_number, old_type, new_type
                - For delete: pot_number, tool_number
                - For life: tool_number, old_life, new_life, life_type
                - For offset: tool_number, offset_type, old_value, new_value
                - For spindle: old_tool_number, new_tool_number
            success: Whether operation succeeded
            error_message: Error message if operation failed
            machine_state: Machine state at time of operation (if available)
        """
        timestamp = datetime.utcnow().isoformat()
        
        _log_entry = {
            "timestamp": timestamp,
            "machine_id": machine_id,
            "operation_type": operation_type,
            "operation_details": operation_details,
            "success": success,
            "error_message": error_message,
            "machine_state": machine_state,
        }
        
        # Log at INFO level for successful operations, WARNING for failures
        if success:
            logger.info(
                f"TOOL_MODIFICATION: machine_id={machine_id}, type={operation_type}, "
                f"details={operation_details}, success=True"
            )
        else:
            logger.warning(
                f"TOOL_MODIFICATION_FAILED: machine_id={machine_id}, type={operation_type}, "
                f"details={operation_details}, error={error_message}"
            )
        
        # Future: Could store in database table for persistent audit trail
        # For now, logging to application logs is sufficient

