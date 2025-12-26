#!/usr/bin/env python3
"""
Simple test script to update tool diameter offset.

Usage:
    python3 test_update_tool_diameter.py <tool_number> <diameter>

Example:
    python3 test_update_tool_diameter.py 1 5.5
    python3 test_update_tool_diameter.py 42 10.0
"""

import sys
import time
from brother_cnc_client import BrotherCNCClient


def update_tool_diameter(tool_number: int, diameter: float) -> bool:
    """
    Update the diameter offset for a tool.

    Args:
        tool_number: Tool number (1-99)
        diameter: Diameter value in mm

    Returns:
        bool: True if successful, False otherwise
    """
    client = BrotherCNCClient()

    print(f"\n{'='*60}")
    print(f"UPDATE TOOL DIAMETER")
    print(f"{'='*60}")
    print(f"Tool Number: {tool_number}")
    print(f"New Diameter: {diameter}mm")
    print(f"{'='*60}\n")

    # Connect to machine
    print("Connecting to machine...")
    if not client.connect():
        print("✗ Failed to connect to machine")
        return False

    try:
        # Read current diameter offset (optional, for reference)
        print(f"\nReading current diameter offset for tool {tool_number}...")
        current = client.read_tool_offset(tool_number=tool_number)
        if current:
            print(f"✓ Current offset data: {current}")
        else:
            print(f"⚠ Could not read current offset (may be normal)")

        # Wait a moment
        time.sleep(0.5)

        # Write new diameter offset
        print(f"\nWriting diameter offset (D-type) = {diameter}mm...")
        success = client.write_tool_offset(
            tool_number=tool_number,
            offset_type='D',
            value=diameter
        )

        if not success:
            print(f"✗ Failed to write diameter offset")
            return False

        print(f"✓ Diameter offset write successful")

        # Wait a moment
        time.sleep(0.5)

        # Read back to verify
        print(f"\nVerifying write by reading tool offset...")
        verified = client.read_tool_offset(tool_number=tool_number)
        if verified:
            print(f"✓ Updated offset data: {verified}")
            print(f"\n✓✓✓ SUCCESS - Tool {tool_number} diameter updated to {diameter}mm")
            return True
        else:
            print(f"⚠ Could not verify (read failed after write)")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    finally:
        print(f"\nDisconnecting...")
        client.disconnect()


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python3 test_update_tool_diameter.py <tool_number> <diameter>")
        print("")
        print("Examples:")
        print("  python3 test_update_tool_diameter.py 1 5.5")
        print("  python3 test_update_tool_diameter.py 42 10.0")
        sys.exit(1)

    try:
        tool_number = int(sys.argv[1])
        diameter = float(sys.argv[2])
    except ValueError:
        print("✗ Error: tool_number must be integer, diameter must be float")
        sys.exit(1)

    # Validate inputs
    if not 1 <= tool_number <= 99:
        print(f"✗ Error: Tool number must be 1-99, got {tool_number}")
        sys.exit(1)

    if diameter < 0:
        print(f"✗ Error: Diameter must be non-negative, got {diameter}")
        sys.exit(1)

    if diameter > 500:
        print(f"⚠ Warning: Diameter {diameter}mm is unusually large (>500mm)")
        response = input("Continue? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled")
            sys.exit(1)

    # Run the update
    success = update_tool_diameter(tool_number, diameter)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
