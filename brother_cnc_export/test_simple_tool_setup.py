#!/usr/bin/env python3
"""
Simple example: Setting up a tool with proper offset before a job.

This demonstrates the primary use case - configuring a tool with
the correct diameter offset before running a job.
"""

from brother_cnc_client import BrotherCNCClient
import sys

def setup_tool_for_job(tool_number, diameter_offset, life_value):
    """
    Complete tool setup workflow.
    
    Args:
        tool_number: Tool number (1-99)
        diameter_offset: Diameter offset in mm
        life_value: Tool life counter value
    
    Returns:
        bool: True if all operations succeeded
    """
    client = BrotherCNCClient()
    
    print(f"\n{'='*60}")
    print(f"SETTING UP TOOL {tool_number} FOR JOB")
    print(f"{'='*60}\n")
    
    # Connect to machine
    print("1. Connecting to machine...")
    if not client.connect():
        print("✗ Connection failed")
        return False
    print("✓ Connected")
    
    try:
        # Read current state (for reference)
        print(f"\n2. Reading current tool {tool_number} state...")
        current = client.read_tool_offset(tool_number=tool_number)
        current_life = client.read_tool_life(tool_number=tool_number)
        print(f"   Current offset: {current}")
        print(f"   Current life: {current_life}")
        
        # Set diameter offset
        print(f"\n3. Setting diameter offset to {diameter_offset}mm...")
        if not client.write_tool_offset(
            tool_number=tool_number,
            offset_type='D',
            value=diameter_offset
        ):
            print("✗ Failed to set offset")
            return False
        
        # Set tool life
        print(f"\n4. Setting tool life counter to {life_value}...")
        if not client.write_tool_life(
            tool_number=tool_number,
            life_value=life_value,
            life_type='TIME'
        ):
            print("✗ Failed to set life")
            return False
        
        # Verify the setup
        print(f"\n5. Verifying setup...")
        verified_offset = client.read_tool_offset(tool_number=tool_number)
        verified_life = client.read_tool_life(tool_number=tool_number)
        print(f"   Verified offset: {verified_offset}")
        print(f"   Verified life: {verified_life}")
        
        print(f"\n{'='*60}")
        print(f"✅ TOOL {tool_number} READY FOR JOB")
        print(f"{'='*60}\n")
        return True
        
    finally:
        print("Disconnecting...")
        client.disconnect()

def main():
    """Example: Set up tool 2 with 0.233mm diameter and 500 time units."""
    if not setup_tool_for_job(
        tool_number=2,
        diameter_offset=0.233,
        life_value=500
    ):
        print("Setup failed")
        sys.exit(1)
    else:
        print("Setup completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()
