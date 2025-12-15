"""Export utilities for generating CSV and JSON files."""
import csv
import json
import io
from typing import List, Dict, Any
from datetime import datetime


def generate_csv(data: List[Dict[str, Any]], headers: List[str]) -> bytes:
    """
    Generate CSV file from list of dictionaries.

    Args:
        data: List of dictionaries containing export data
        headers: List of column headers

    Returns:
        CSV file content as bytes
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')

    writer.writeheader()
    writer.writerows(data)

    return output.getvalue().encode('utf-8')


def generate_json_export(data: Any) -> bytes:
    """
    Generate formatted JSON for export.

    Args:
        data: Any JSON-serializable data structure

    Returns:
        JSON file content as bytes
    """
    # Custom JSON encoder for datetime objects
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    return json.dumps(data, indent=2, default=json_serial).encode('utf-8')


def flatten_tool_data_for_csv(
    tool_number: int,
    diameter: float,
    description: str,
    total_runtime_seconds: float,
    total_programs: int,
    total_runs: int,
    programs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Flatten tool data with per-program operations for CSV export.

    Creates one row per program operation with tool and program data repeated.

    Args:
        tool_number: Tool number
        diameter: Tool diameter
        description: Tool description
        total_runtime_seconds: Total estimated runtime
        total_programs: Number of programs using tool
        total_runs: Number of production runs
        programs: List of program dictionaries with nested operations

    Returns:
        List of flattened dictionaries, one per program operation
    """
    if not programs:
        # No programs - return single row with tool data only
        return [{
            'tool_number': tool_number,
            'diameter': diameter,
            'description': description,
            'total_runtime_seconds': total_runtime_seconds,
            'total_programs': total_programs,
            'total_runs': total_runs,
            'program_id': None,
            'program_filename': '',
            'program_version': None,
            'program_runs': 0,
            'operation_name': '',
            'spindle_speed': None,
            'feedrate_cutting': None,
            'feedrate_plunge': None,
            'feedrate_finish': None,
            'feedrate_entry': None,
            'feedrate_exit': None,
            'feedrate_direct': None,
            'feedrate_transition': None
        }]

    rows = []
    for prog in programs:
        program_id = prog.get('program_id')
        program_filename = prog.get('filename', '')
        program_version = prog.get('version')
        program_runs = prog.get('production_runs', 0)
        operations = prog.get('operations', [])

        if not operations:
            # Program with no operations - single row for program
            rows.append({
                'tool_number': tool_number,
                'diameter': diameter,
                'description': description,
                'total_runtime_seconds': total_runtime_seconds,
                'total_programs': total_programs,
                'total_runs': total_runs,
                'program_id': program_id,
                'program_filename': program_filename,
                'program_version': program_version,
                'program_runs': program_runs,
                'operation_name': '',
                'spindle_speed': None,
                'feedrate_cutting': None,
                'feedrate_plunge': None,
                'feedrate_finish': None,
                'feedrate_entry': None,
                'feedrate_exit': None,
                'feedrate_direct': None,
                'feedrate_transition': None
            })
        else:
            # Create row for each operation in program
            for op in operations:
                rows.append({
                    'tool_number': tool_number,
                    'diameter': diameter,
                    'description': description,
                    'total_runtime_seconds': total_runtime_seconds,
                    'total_programs': total_programs,
                    'total_runs': total_runs,
                    'program_id': program_id,
                    'program_filename': program_filename,
                    'program_version': program_version,
                    'program_runs': program_runs,
                    'operation_name': op.get('operation_name', ''),
                    'spindle_speed': op.get('spindle_speed'),
                    'feedrate_cutting': op.get('feedrate_cutting'),
                    'feedrate_plunge': op.get('feedrate_plunge'),
                    'feedrate_finish': op.get('feedrate_finish'),
                    'feedrate_entry': op.get('feedrate_entry'),
                    'feedrate_exit': op.get('feedrate_exit'),
                    'feedrate_direct': op.get('feedrate_direct'),
                    'feedrate_transition': op.get('feedrate_transition')
                })

    return rows


# CSV headers for tool export
TOOL_EXPORT_CSV_HEADERS = [
    'tool_number',
    'diameter',
    'description',
    'total_runtime_seconds',
    'total_programs',
    'total_runs',
    'program_id',
    'program_filename',
    'program_version',
    'program_runs',
    'operation_name',
    'spindle_speed',
    'feedrate_cutting',
    'feedrate_plunge',
    'feedrate_finish',
    'feedrate_entry',
    'feedrate_exit',
    'feedrate_direct',
    'feedrate_transition'
]
