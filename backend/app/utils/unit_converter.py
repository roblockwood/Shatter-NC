"""Unit conversion utilities for CNC machine data.

Provides conversion between inches and millimeters, and formatting utilities
for displaying dimensional values with correct unit suffixes.
"""
from typing import Literal


UnitType = Literal['in', 'mm']


def convert_inches_to_mm(value: float) -> float:
    """
    Convert inches to millimeters.
    
    Args:
        value: Value in inches
        
    Returns:
        Value in millimeters
    """
    return value * 25.4


def convert_mm_to_inches(value: float) -> float:
    """
    Convert millimeters to inches.
    
    Args:
        value: Value in millimeters
        
    Returns:
        Value in inches
    """
    return value / 25.4


def convert_dimension(value: float, from_units: UnitType, to_units: UnitType) -> float:
    """
    Convert a dimensional value from one unit system to another.
    
    Args:
        value: The value to convert
        from_units: Source unit system ('in' or 'mm')
        to_units: Target unit system ('in' or 'mm')
        
    Returns:
        Converted value
        
    Raises:
        ValueError: If unit types are invalid
    """
    if from_units not in ('in', 'mm') or to_units not in ('in', 'mm'):
        raise ValueError(f"Invalid unit type. Must be 'in' or 'mm', got '{from_units}' -> '{to_units}'")
    
    # No conversion needed
    if from_units == to_units:
        return value
    
    # Convert inches to millimeters
    if from_units == 'in' and to_units == 'mm':
        return convert_inches_to_mm(value)
    
    # Convert millimeters to inches
    if from_units == 'mm' and to_units == 'in':
        return convert_mm_to_inches(value)
    
    # Should never reach here, but satisfy type checker
    return value


def format_dimension(value: float | None, units: UnitType = 'in', decimals: int = 4) -> str:
    """
    Format a dimensional value with appropriate unit suffix.
    
    Args:
        value: The value to format (None/NaN will return placeholder)
        units: Unit system ('in' or 'mm')
        decimals: Number of decimal places
        
    Returns:
        Formatted string with unit suffix (e.g., "0.2500 in" or "6.3500 mm")
        Returns "────" if value is None or NaN
    """
    if value is None:
        return "────"
    
    try:
        # Check for NaN
        if value != value:  # NaN check
            return "────"
        
        formatted = f"{value:.{decimals}f}"
        suffix = '"' if units == 'in' else ' mm'
        return f"{formatted}{suffix}"
    except (TypeError, ValueError):
        return "────"

