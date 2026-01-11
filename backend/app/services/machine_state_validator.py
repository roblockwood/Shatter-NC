"""
Machine State Validation Service

Validates machine state before allowing write operations (tool modifications, ATC changes, etc.).
Ensures machine is in a safe state to prevent operations during active machining, editing, or error conditions.
"""
from typing import Tuple, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session

from app.models.machine import Machine
from app.api.status import get_machine_status

logger = logging.getLogger(__name__)


class MachineStateValidator:
    """Validates machine state for write operations."""
    
    # Mode codes from MEM data (0=Manual, 1=MDI, 2=Memory, 3=Edit, 4=MDI manual, 5=Memory edit)
    UNSAFE_MODES = {3, 4, 5}  # Edit, MDI manual, Memory edit
    
    # Operation status codes from MEM data (0=Reset, 1=Operation, 2=Temporary stop, 3=Block stop)
    UNSAFE_OPERATION_STATUSES = {1, 2, 3}  # Operation, Temporary stop, Block stop
    
    async def validate_safe_for_write(
        self,
        machine_id: int,
        operation_type: str,
        db: Session
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate machine is in safe state for write operations.
        
        Uses minimal, operation-specific validation - only blocks definitively unsafe states.
        The machine firmware will reject operations with appropriate error codes if truly unsafe.
        
        Blocked states (all operations):
        - PRD3 status "operating" - Machine is actively running
        - MEM mode 2 (Memory operation) - Program is running
        
        Blocked states (tool assignment/deletion only, not color changes):
        - MEM mode 3, 4, 5 (Edit, MDI manual, Memory edit)
        - MEM operation_status 1, 2, 3 (Operation, Temporary stop, Block stop)
        
        Allowed (machine will reject via error codes if unsafe):
        - PRD3 status "error" - Machine will reject if error prevents operation
        - Active alarms - Machine will reject if alarms prevent operation
        - Edit modes for color changes - Machine will reject if edit mode prevents color change
        
        Args:
            machine_id: Machine ID to validate
            operation_type: Type of operation - "tool_color", "tool_assignment", "tool_delete", 
                          "spindle_tool", "tool_type", "tool_life", "tool_offset"
            db: Database session
            
        Returns:
            Tuple of (is_safe: bool, error_message: Optional[str], status_data: Optional[Dict])
            - is_safe: True if machine is safe for write operations
            - error_message: Human-readable error message if unsafe
            - status_data: Current machine status data (for UI display)
        """
        # Fetch machine record
        db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not db_machine:
            return False, f"Machine {machine_id} not found", None
        
        try:
            # Get current machine status (includes PRD3, alarms)
            # We need to extend this to also fetch MEM data for mode and operation_status
            from app.clients.telnet_client import get_or_create_connection
            from app.parsers.mem_parser_v2 import parse_mem_v2
            
            telnet_client = await get_or_create_connection(
                ip_address=db_machine.ip_address,
                port=10000,
                timeout=10
            )
            
            control_version = await telnet_client.detect_control_type()
            
            # Get MEM data to check mode and operation_status
            mem_data = await telnet_client.get_memory_data(verbose=False)
            mem_parsed = None
            if mem_data:
                mem_parsed = parse_mem_v2(mem_data.encode('utf-8'), control_version=control_version)
            
            # Get machine status (PRD3, alarms)
            # We'll use the internal logic from get_machine_status but directly here
            from app.parsers.prd3_parser_v2 import parse_prd3_v2
            from app.parsers.alarm_parser_v2 import parse_alarm_v2
            from app.utils.alarm_code_lookup import enrich_alarm_with_lookup
            
            prd3_data = await telnet_client.get_prd3_data(control_version=control_version, verbose=False)
            prd3_parsed = None
            if prd3_data:
                prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)
            
            # Get alarms
            alarm_data_raw = await telnet_client.get_alarm_data(verbose=False)
            alarms = []
            if alarm_data_raw:
                alarm_parsed = parse_alarm_v2(alarm_data_raw.encode('utf-8'), control_version=None)
                all_alarms = alarm_parsed.get("alarms", []) + alarm_parsed.get("loading_alarms", [])
                alarms = [enrich_alarm_with_lookup(alarm) for alarm in all_alarms]
            
            # Build status data for return
            status_data = {
                "machine_id": machine_id,
                "machine_name": db_machine.name,
            }
            
            # Check PRD3 status - only block known unsafe states
            if prd3_parsed and prd3_parsed.get("current_status"):
                current_status_data = prd3_parsed["current_status"]
                machine_status = current_status_data.get("status")
                status_code = current_status_data.get("current_status")
                status_data["status"] = machine_status
                status_data["status_code"] = status_code
                
                # Only block "operating" status - this is definitively unsafe
                # Allow other statuses (standby, off, error, stopped) - let the machine reject via error codes if needed
                if machine_status == "operating":
                    return False, "Machine is currently running a program. Stop the program before making changes.", status_data
            else:
                # PRD3 data not available - allow it and let the machine reject if needed
                logger.warning(f"PRD3 data not available for machine {machine_id}, allowing operation (machine will reject if unsafe)")
                # Don't block - let the machine decide
            
            # Check MEM mode and operation_status - these are the critical checks
            if mem_parsed:
                mode = mem_parsed.get("mode")
                operation_status = mem_parsed.get("operation_status")
                status_data["mode"] = mode
                status_data["operation_status"] = operation_status
                
                # Block editing modes that prevent ATC changes
                # Mode 2 = Memory operation (actively running program)
                # Mode 3 = Edit, Mode 4 = MDI manual, Mode 5 = Memory edit (editing modes)
                if mode is not None:
                    if mode == 2:  # Memory operation - actively running
                        return False, "Machine is running a program. Stop the program before making changes.", status_data
                    elif mode in self.UNSAFE_MODES:  # Edit modes
                        mode_names = {3: "Edit", 4: "MDI manual", 5: "Memory edit"}
                        mode_name = mode_names.get(mode, f"Mode {mode}")
                        # For color changes, edit modes might be OK, but for tool assignment, block
                        if operation_type in ("tool_assignment", "tool_delete", "spindle_tool"):
                            return False, f"Machine is in {mode_name} mode. Exit edit mode before making tool assignments.", status_data
                        # For color changes, just warn but allow
                        logger.info(f"Machine in {mode_name} mode for {operation_type} - allowing (machine will reject if unsafe)")
                
                # Check operation_status - block if actively operating
                if operation_status is not None and operation_status in self.UNSAFE_OPERATION_STATUSES:
                    status_names = {1: "Operation", 2: "Temporary stop", 3: "Block stop"}
                    status_name = status_names.get(operation_status, f"Status {operation_status}")
                    # Block for tool assignments, allow for color changes (machine will reject if needed)
                    if operation_type in ("tool_assignment", "tool_delete", "spindle_tool"):
                        return False, f"Machine operation in progress ({status_name}). Stop the operation before making tool changes.", status_data
                    # For color changes, warn but allow - machine will reject with error code if unsafe
                    logger.info(f"Machine operation_status={operation_status} for {operation_type} - allowing (machine will reject if unsafe)")
            else:
                # MEM data not available - allow it and let the machine reject if needed
                logger.warning(f"MEM data not available for machine {machine_id}, allowing operation (machine will reject if unsafe)")
            
            # Don't block on alarms - let the machine decide via error codes
            # Some alarms may not prevent tool changes, and the machine will reject appropriately
            if alarms:
                logger.info(f"Machine has {len(alarms)} active alarms - allowing operation (machine will reject if alarms prevent changes)")
            
            # All checks passed
            status_data["alarms"] = alarms
            return True, None, status_data
            
        except Exception as e:
            logger.error(f"Error validating machine state for machine {machine_id}: {e}")
            return False, f"Error checking machine state: {str(e)}", None

