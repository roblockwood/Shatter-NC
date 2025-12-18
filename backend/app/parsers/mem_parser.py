"""Parser for MEM.NC memory information file.

MEM.NC contains the currently active program name on the Brother CNC machine.
This file is small (typically ~31 bytes) and contains the O-number of the active program.

Format may vary, but typically contains the program O-number.
Example formats:
- O2045
- O2045.NC
- O2045\n
- O2045\r\n
"""
from typing import Dict, Any, Optional
import re


class MEMParser:
    """Parser for MEM.NC memory information file."""

    def __init__(self, content: bytes):
        """
        Initialize parser with MEM.NC file content.

        Args:
            content: Raw bytes from MEM.NC file
        """
        # Decode and clean content (strip null bytes and whitespace)
        self.content = content.decode('utf-8', errors='replace').rstrip('\x00\r\n\t ')
        self.lines = [line.strip() for line in self.content.split('\n') if line.strip()]

    def parse(self) -> Dict[str, Any]:
        """
        Parse MEM.NC and extract the active program name.

        Returns:
            Dict containing:
                - program_name: O-number of active program (e.g., "O2045")
        """
        import logging
        logger = logging.getLogger(__name__)
        
        program_name = None
        
        # Log raw content for debugging
        logger.debug(f"Parsing mem.nc - raw content: {repr(self.content)}")
        logger.debug(f"Parsing mem.nc - lines: {self.lines}")

        # Try to find O-number pattern in the content
        # Pattern: O followed by 4 digits (e.g., O2045, O2045.NC)
        o_number_pattern = re.compile(r'O(\d{4})(?:\.NC)?', re.IGNORECASE)
        
        # Search in all lines
        for line in self.lines:
            match = o_number_pattern.search(line)
            if match:
                # Extract O-number (always uppercase, no extension)
                program_name = f"O{match.group(1)}"
                logger.debug(f"Found program_name via regex: {program_name}")
                break
        
        # If no match found, try the first non-empty line as-is
        if not program_name and self.lines:
            first_line = self.lines[0].strip()
            logger.debug(f"No regex match, trying first line: {repr(first_line)}")
            # If it looks like an O-number, use it
            if re.match(r'O\d{4}', first_line, re.IGNORECASE):
                program_name = first_line.upper()
                # Remove .NC extension if present
                if program_name.endswith('.NC'):
                    program_name = program_name[:-3]
                logger.debug(f"Found program_name from first line: {program_name}")
        
        # If still no match, try extracting any 4-digit number and prepending O
        if not program_name:
            digit_pattern = re.compile(r'(\d{4})')
            for line in self.lines:
                match = digit_pattern.search(line)
                if match:
                    program_name = f"O{match.group(1)}"
                    logger.debug(f"Found program_name via digit extraction: {program_name}")
                    break

        if not program_name:
            logger.warning(f"Could not extract program_name from mem.nc. Content: {repr(self.content)}")

        return {
            "program_name": program_name
        }


def parse_mem(content: bytes) -> Dict[str, Any]:
    """
    Convenience function to parse MEM.NC content.

    Args:
        content: Raw bytes from MEM.NC file

    Returns:
        Parsed memory data with program_name
    """
    parser = MEMParser(content)
    return parser.parse()

