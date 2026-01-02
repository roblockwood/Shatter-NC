/**
 * Unit formatting utilities for displaying dimensional values.
 * 
 * Formats values with appropriate unit suffixes based on machine configuration.
 */

export type UnitType = 'in' | 'mm';

// Re-export as a value for better compatibility
export const UnitTypeValues = ['in', 'mm'] as const;

/**
 * Format a dimensional value with appropriate unit suffix.
 * 
 * @param value - The value to format (null/undefined/NaN will return placeholder)
 * @param units - Unit system ('in' for inches, 'mm' for millimeters). Defaults to 'in'.
 * @param decimals - Number of decimal places. Defaults to 4.
 * @returns Formatted string with unit suffix (e.g., "0.2500 in" or "6.3500 mm")
 *          Returns "────" if value is null, undefined, or NaN
 */
export function formatDimension(
  value: number | null | undefined,
  units: UnitType = 'in',
  decimals: number = 4
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '────';
  }
  
  const formatted = value.toFixed(decimals);
  const suffix = units === 'in' ? '"' : ' mm';
  return `${formatted}${suffix}`;
}

/**
 * Get the unit suffix for a given unit type.
 * 
 * @param units - Unit system ('in' or 'mm')
 * @returns Unit suffix string ('"' for inches, ' mm' for millimeters)
 */
export function getUnitSuffix(units: UnitType): string {
  return units === 'in' ? '"' : ' mm';
}

