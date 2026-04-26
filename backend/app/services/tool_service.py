"""Tool management service - core business logic for tool analysis."""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from app.models.program import Program
from app.models.event import ProductionRun, AlarmEvent
from app.models.machine import Machine
from app.schemas.tools import (
    ToolSummary,
    ToolSummaryResponse,
    ToolDetail,
    OperationStats,
    MachineUsage,
    ProgramUsage,
    AlarmSummary,
    ToolHistoryResponse,
    ProductionRunSummary
)


class ToolService:
    """Service for tool analysis and data aggregation."""

    @staticmethod
    def get_tool_summary(db: Session) -> ToolSummaryResponse:
        """
        Get aggregated summary of all tools across all programs.

        Extracts tools from program_metadata JSONB and aggregates:
        - Unique tool numbers with specifications
        - Program usage counts
        - Production run counts
        - Estimated runtime (program duration / tool count)
        - Machine usage
        - Operation types

        Returns:
            ToolSummaryResponse with list of all tools and summary stats
        """
        # Extract unique tools from program_metadata JSONB
        query = text("""
            SELECT
                (tool_data->>'tool_number')::int as tool_number,
                (tool_data->>'diameter')::float as diameter,
                tool_data->>'description' as description,
                COUNT(DISTINCT p.id) as programs_using,
                jsonb_agg(DISTINCT tool_data->'operations') as operations_agg
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE p.is_active = TRUE
            GROUP BY tool_data->>'tool_number',
                     tool_data->>'diameter',
                     tool_data->>'description'
            ORDER BY (tool_data->>'tool_number')::int
        """)

        total_programs_query = text(
            "SELECT COUNT(*) FROM programs WHERE is_active = TRUE"
        )

        result = db.execute(query)
        tools_data = result.fetchall()
        total_programs = db.execute(total_programs_query).scalar() or 0

        tools = []
        total_production_runs = 0

        for row in tools_data:
            tool_number = row.tool_number
            diameter = row.diameter
            description = row.description or "UNKNOWN"

            # Get programs using this tool
            programs_using = row.programs_using

            # Extract operation types
            operation_types = set()
            if row.operations_agg:
                for ops_array in row.operations_agg:
                    if ops_array:
                        for op in ops_array:
                            if op and 'operation_name' in op and op['operation_name']:
                                operation_types.add(op['operation_name'])

            # Get production run count and estimated runtime
            stats = ToolService._get_tool_production_stats(db, tool_number)

            tools.append(ToolSummary(
                tool_number=tool_number,
                diameter=diameter,
                description=description,
                programs_using=programs_using,
                estimated_runtime_seconds=stats['estimated_runtime_seconds'],
                total_runs=stats['total_runs'],
                machines_used=stats['machines_used'],
                operation_types=sorted(list(operation_types))
            ))

            total_production_runs += stats['total_runs']

        return ToolSummaryResponse(
            total_unique_tools=len(tools),
            total_programs=total_programs,
            total_production_runs=total_production_runs,
            tools=tools
        )

    @staticmethod
    def _get_tool_production_stats(db: Session, tool_number: int) -> Dict[str, Any]:
        """
        Get production run statistics for a specific tool.

        Args:
            db: Database session
            tool_number: Tool number to query

        Returns:
            Dictionary with estimated_runtime_seconds, total_runs, machines_used
        """
        # Get all programs that use this tool
        query = text("""
            SELECT DISTINCT p.id
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        program_ids = [row.id for row in result.fetchall()]

        if not program_ids:
            return {
                'estimated_runtime_seconds': 0.0,
                'total_runs': 0,
                'machines_used': []
            }

        # Get production runs for these programs
        runs = db.query(ProductionRun).filter(
            ProductionRun.program_id.in_(program_ids)
        ).all()

        total_runtime = 0.0
        machines_used = set()

        for run in runs:
            if run.machine_id:
                machines_used.add(run.machine_id)

            # Estimate tool runtime: divide program runtime by number of tools
            if run.duration_seconds and run.program_id:
                program = db.query(Program).filter(Program.id == run.program_id).first()
                if program and program.program_metadata:
                    tools = program.program_metadata.get('tools', [])
                    tool_count = len(tools) if tools else 1
                    estimated_tool_time = run.duration_seconds / tool_count
                    total_runtime += estimated_tool_time

        return {
            'estimated_runtime_seconds': total_runtime,
            'total_runs': len(runs),
            'machines_used': sorted(list(machines_used))
        }

    @staticmethod
    def get_tool_detail(db: Session, tool_number: int) -> ToolDetail:
        """
        Get detailed analysis for a specific tool.

        Args:
            db: Database session
            tool_number: Tool number to analyze

        Returns:
            ToolDetail with specifications, usage stats, operations, programs, alarms
        """
        # Get tool specifications from all programs
        query = text("""
            SELECT
                (tool_data->>'diameter')::float as diameter,
                (tool_data->>'corner_radius')::float as corner_radius,
                (tool_data->>'length_total')::float as length_total,
                tool_data->>'description' as description
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        specs_data = result.fetchall()

        if not specs_data:
            # Tool not found - return empty detail
            return ToolDetail(
                tool_number=tool_number,
                specifications={
                    'diameter_range': [0, 0],
                    'descriptions': [],
                    'length_range': [0, 0]
                },
                usage_statistics={
                    'total_programs': 0,
                    'total_production_runs': 0,
                    'estimated_runtime_seconds': 0,
                    'total_parts_produced': 0
                },
                machines=[],
                programs=[],
                alarms=[]
            )

        # Extract specifications
        diameters = [row.diameter for row in specs_data if row.diameter is not None]
        lengths = [row.length_total for row in specs_data if row.length_total is not None]
        descriptions = list(set([row.description for row in specs_data if row.description]))

        specifications = {
            'diameter_range': [min(diameters), max(diameters)] if diameters else [0, 0],
            'descriptions': descriptions,
            'length_range': [min(lengths), max(lengths)] if lengths else [0, 0]
        }

        # Get usage statistics
        usage_stats = ToolService._get_detailed_usage_stats(db, tool_number)

        # Get machine usage breakdown
        machine_usage = ToolService._get_machine_usage(db, tool_number)

        # Get program usage (with operations nested in each program)
        programs = ToolService._get_program_usage(db, tool_number)

        # Get alarm correlation
        alarms = ToolService._get_alarm_correlation(db, tool_number)

        return ToolDetail(
            tool_number=tool_number,
            specifications=specifications,
            usage_statistics=usage_stats,
            machines=machine_usage,
            programs=programs,
            alarms=alarms
        )

    @staticmethod
    def _get_detailed_usage_stats(db: Session, tool_number: int) -> Dict[str, Any]:
        """Get detailed usage statistics for a tool."""
        # Get program IDs using this tool
        query = text("""
            SELECT DISTINCT p.id
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        program_ids = [row.id for row in result.fetchall()]

        if not program_ids:
            return {
                'total_programs': 0,
                'total_production_runs': 0,
                'estimated_runtime_seconds': 0,
                'total_parts_produced': 0
            }

        # Get production runs
        runs = db.query(ProductionRun).filter(
            ProductionRun.program_id.in_(program_ids)
        ).all()

        total_runtime = 0.0
        total_parts = 0

        for run in runs:
            if run.duration_seconds and run.program_id:
                program = db.query(Program).filter(Program.id == run.program_id).first()
                if program and program.program_metadata:
                    tools = program.program_metadata.get('tools', [])
                    tool_count = len(tools) if tools else 1
                    estimated_tool_time = run.duration_seconds / tool_count
                    total_runtime += estimated_tool_time

            if run.parts_produced:
                total_parts += run.parts_produced

        return {
            'total_programs': len(program_ids),
            'total_production_runs': len(runs),
            'estimated_runtime_seconds': total_runtime,
            'total_parts_produced': total_parts
        }

    @staticmethod
    def _get_machine_usage(db: Session, tool_number: int) -> List[MachineUsage]:
        """Get per-machine usage breakdown for a tool."""
        # Get program IDs
        query = text("""
            SELECT DISTINCT p.id
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        program_ids = [row.id for row in result.fetchall()]

        if not program_ids:
            return []

        # Aggregate by machine
        machine_stats = defaultdict(lambda: {'runs': 0, 'runtime': 0.0})

        runs = db.query(ProductionRun).filter(
            ProductionRun.program_id.in_(program_ids)
        ).all()

        for run in runs:
            if run.machine_id:
                machine_stats[run.machine_id]['runs'] += 1

                if run.duration_seconds and run.program_id:
                    program = db.query(Program).filter(Program.id == run.program_id).first()
                    if program and program.program_metadata:
                        tools = program.program_metadata.get('tools', [])
                        tool_count = len(tools) if tools else 1
                        estimated_tool_time = run.duration_seconds / tool_count
                        machine_stats[run.machine_id]['runtime'] += estimated_tool_time

        # Build response with machine names
        machine_usage = []
        for machine_id, stats in machine_stats.items():
            machine = db.query(Machine).filter(Machine.id == machine_id).first()
            machine_name = machine.name if machine else f"Machine {machine_id}"

            machine_usage.append(MachineUsage(
                machine_id=machine_id,
                machine_name=machine_name,
                production_runs=stats['runs'],
                runtime_seconds=stats['runtime']
            ))

        # Sort by runtime descending
        machine_usage.sort(key=lambda x: x.runtime_seconds, reverse=True)

        return machine_usage

    @staticmethod
    def _get_operation_stats(db: Session, tool_number: int) -> List[OperationStats]:
        """Get operation-level speed/feed statistics for a tool."""
        query = text("""
            SELECT
                operation_data->>'operation_name' as operation_name,
                (operation_data->>'spindle_speed')::float as spindle_speed,
                (operation_data->>'feedrate_cutting')::float as feedrate_cutting,
                (operation_data->>'feedrate_plunge')::float as feedrate_plunge,
                (operation_data->>'feedrate_finish')::float as feedrate_finish,
                (operation_data->>'feedrate_entry')::float as feedrate_entry,
                (operation_data->>'feedrate_exit')::float as feedrate_exit,
                (operation_data->>'feedrate_direct')::float as feedrate_direct,
                (operation_data->>'feedrate_transition')::float as feedrate_transition
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data,
                 jsonb_array_elements(tool_data->'operations') as operation_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        operations_data = result.fetchall()

        # Aggregate by operation name
        op_aggregates = defaultdict(lambda: {
            'spindle_speed': [],
            'feedrate_cutting': [],
            'feedrate_plunge': [],
            'feedrate_finish': [],
            'feedrate_entry': [],
            'feedrate_exit': [],
            'feedrate_direct': [],
            'feedrate_transition': []
        })

        for row in operations_data:
            op_name = row.operation_name or "UNNAMED"

            if row.spindle_speed is not None:
                op_aggregates[op_name]['spindle_speed'].append(row.spindle_speed)
            if row.feedrate_cutting is not None:
                op_aggregates[op_name]['feedrate_cutting'].append(row.feedrate_cutting)
            if row.feedrate_plunge is not None:
                op_aggregates[op_name]['feedrate_plunge'].append(row.feedrate_plunge)
            if row.feedrate_finish is not None:
                op_aggregates[op_name]['feedrate_finish'].append(row.feedrate_finish)
            if row.feedrate_entry is not None:
                op_aggregates[op_name]['feedrate_entry'].append(row.feedrate_entry)
            if row.feedrate_exit is not None:
                op_aggregates[op_name]['feedrate_exit'].append(row.feedrate_exit)
            if row.feedrate_direct is not None:
                op_aggregates[op_name]['feedrate_direct'].append(row.feedrate_direct)
            if row.feedrate_transition is not None:
                op_aggregates[op_name]['feedrate_transition'].append(row.feedrate_transition)

        # Build response with min/max/avg
        operations = []
        for op_name, data in op_aggregates.items():
            def calc_stats(values: List[float]) -> Optional[Dict[str, float]]:
                if not values:
                    return None
                return {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values)
                }

            operations.append(OperationStats(
                operation_name=op_name,
                occurrences=max(
                    len(data['spindle_speed']),
                    len(data['feedrate_cutting']),
                    1
                ),
                spindle_speed=calc_stats(data['spindle_speed']),
                feedrate_cutting=calc_stats(data['feedrate_cutting']),
                feedrate_plunge=calc_stats(data['feedrate_plunge']),
                feedrate_finish=calc_stats(data['feedrate_finish']),
                feedrate_entry=calc_stats(data['feedrate_entry']),
                feedrate_exit=calc_stats(data['feedrate_exit']),
                feedrate_direct=calc_stats(data['feedrate_direct']),
                feedrate_transition=calc_stats(data['feedrate_transition'])
            ))

        # Sort by occurrences descending
        operations.sort(key=lambda x: x.occurrences, reverse=True)

        return operations

    @staticmethod
    def _get_program_usage(db: Session, tool_number: int) -> List[ProgramUsage]:
        """Get list of programs using a specific tool with their operations."""
        query = text("""
            SELECT DISTINCT
                p.id,
                p.original_filename,
                p.version_number,
                p.program_metadata,
                (
                    SELECT pd.deployed_path
                    FROM program_deployments pd
                    WHERE pd.program_id = p.id
                      AND pd.is_current = TRUE
                    ORDER BY pd.deployed_at DESC
                    LIMIT 1
                ) AS deployed_path
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
            ORDER BY p.original_filename, p.version_number DESC
        """)

        result = db.execute(query, {"tool_number": tool_number})
        programs_data = result.fetchall()

        programs = []
        for row in programs_data:
            # Get production run count and last run
            runs = db.query(ProductionRun).filter(
                ProductionRun.program_id == row.id
            ).order_by(ProductionRun.started_at.desc()).all()

            last_run = runs[0].started_at if runs else None

            # Extract operations for this tool from this program's metadata
            operations = []
            if row.program_metadata and 'tools' in row.program_metadata:
                for tool in row.program_metadata['tools']:
                    if tool.get('tool_number') == tool_number:
                        # Found the tool - extract its operations
                        tool_operations = tool.get('operations', [])
                        for op in tool_operations:
                            operations.append(OperationStats(
                                operation_name=op.get('operation_name'),
                                spindle_speed=op.get('spindle_speed'),
                                feedrate_cutting=op.get('feedrate_cutting'),
                                feedrate_plunge=op.get('feedrate_plunge'),
                                feedrate_finish=op.get('feedrate_finish'),
                                feedrate_entry=op.get('feedrate_entry'),
                                feedrate_exit=op.get('feedrate_exit'),
                                feedrate_direct=op.get('feedrate_direct'),
                                feedrate_transition=op.get('feedrate_transition')
                            ))
                        break  # Found the tool, no need to continue

            programs.append(ProgramUsage(
                program_id=row.id,
                filename=row.original_filename,
                deployed_path=row.deployed_path,
                version=row.version_number,
                production_runs=len(runs),
                last_run=last_run,
                operations=operations
            ))

        return programs

    @staticmethod
    def _get_alarm_correlation(db: Session, tool_number: int) -> List[AlarmSummary]:
        """Get alarm correlation for programs using a specific tool."""
        # Get program IDs
        query = text("""
            SELECT DISTINCT p.id
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        program_ids = [row.id for row in result.fetchall()]

        if not program_ids:
            return []

        # Get alarms for these programs
        alarms = db.query(AlarmEvent).filter(
            AlarmEvent.program_id.in_(program_ids)
        ).all()

        # Aggregate by alarm code
        alarm_aggregates = defaultdict(lambda: {'message': '', 'times': []})

        for alarm in alarms:
            alarm_aggregates[alarm.alarm_code]['message'] = alarm.alarm_message
            alarm_aggregates[alarm.alarm_code]['times'].append(alarm.time)

        # Build response
        alarm_summaries = []
        for code, data in alarm_aggregates.items():
            alarm_summaries.append(AlarmSummary(
                alarm_code=code,
                alarm_message=data['message'],
                occurrences=len(data['times']),
                last_occurrence=max(data['times']) if data['times'] else None
            ))

        # Sort by occurrences descending
        alarm_summaries.sort(key=lambda x: x.occurrences, reverse=True)

        return alarm_summaries

    @staticmethod
    def get_tool_history(
        db: Session,
        tool_number: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        machine_id: Optional[int] = None,
        limit: int = 100
    ) -> ToolHistoryResponse:
        """
        Get production run history for a specific tool.

        Args:
            db: Database session
            tool_number: Tool number to query
            start_date: Optional start date filter
            end_date: Optional end date filter
            machine_id: Optional machine ID filter
            limit: Maximum number of runs to return (default 100, max 1000)

        Returns:
            ToolHistoryResponse with list of production runs
        """
        # Limit to max 1000
        limit = min(limit, 1000)

        # Get program IDs using this tool
        query = text("""
            SELECT DISTINCT p.id
            FROM programs p,
                 jsonb_array_elements(p.program_metadata->'tools') as tool_data
            WHERE (tool_data->>'tool_number')::int = :tool_number
              AND p.is_active = TRUE
        """)

        result = db.execute(query, {"tool_number": tool_number})
        program_ids = [row.id for row in result.fetchall()]

        if not program_ids:
            return ToolHistoryResponse(
                tool_number=tool_number,
                total_runs=0,
                runs=[]
            )

        # Build query with filters
        query = db.query(ProductionRun).filter(
            ProductionRun.program_id.in_(program_ids)
        )

        if start_date:
            query = query.filter(ProductionRun.started_at >= start_date)

        if end_date:
            query = query.filter(ProductionRun.started_at <= end_date)

        if machine_id:
            query = query.filter(ProductionRun.machine_id == machine_id)

        query = query.order_by(ProductionRun.started_at.desc()).limit(limit)

        runs = query.all()

        # Build response
        run_summaries = []
        for run in runs:
            machine = db.query(Machine).filter(Machine.id == run.machine_id).first()
            machine_name = machine.name if machine else f"Machine {run.machine_id}"

            run_summaries.append(ProductionRunSummary(
                run_id=run.id,
                machine_id=run.machine_id,
                machine_name=machine_name,
                program_name=run.program_name or "UNKNOWN",
                started_at=run.started_at,
                ended_at=run.ended_at,
                duration_seconds=run.duration_seconds,
                parts_produced=run.parts_produced or 0,
                alarm_count=run.alarm_count or 0,
                completion_status=run.completion_status
            ))

        return ToolHistoryResponse(
            tool_number=tool_number,
            total_runs=len(runs),
            runs=run_summaries
        )
