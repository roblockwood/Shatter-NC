#!/usr/bin/env python3
"""Test script to verify MEM and POSNI schema-based parsers on machine.

Note: If Shatter backend is running, it may hold the Telnet connection (single connection limit).
This script will close any existing connection, run tests, then restore the connection.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.clients.telnet_client import get_or_create_connection, close_connection
from app.parsers.mem_parser_v2 import parse_mem_v2
from app.parsers.posni_parser_v2 import parse_posni_v2


async def test_mem_schema(ip_address: str = "192.168.86.89", port: int = 10000):
    """Test MEM schema-based parser."""
    print(f"\n{'='*60}")
    print(f"Testing MEM Schema Parser on {ip_address}:{port}")
    print(f"{'='*60}\n")
    
    try:
        # Get connection for testing (should be fresh after main() closed existing connection)
        client = await get_or_create_connection(
            ip_address=ip_address,
            port=port,
            timeout=15  # Longer timeout
        )
        
        # Check connection status
        print(f"Connection status: {client._connected}")
        if not client._connected:
            print("Attempting to connect...")
            connected = await client.connect()
            if not connected:
                print("✗ Failed to connect to machine")
                return False
        
        # Fetch MEM data
        print("Fetching MEM data via Telnet...")
        mem_data = await client.get_memory_data(verbose=False)  # Disable verbose for cleaner output
        
        if not mem_data:
            print("✗ Failed to fetch MEM data (may be CM7500 error - machine has data file open)")
            print("  → Close any open data files on the machine and try again")
            return False
        
        print(f"✓ MEM data received ({len(mem_data)} bytes)")
        print(f"\nRaw MEM content: {repr(mem_data)}")
        print(f"Raw MEM content (readable): {mem_data}")
        
        # Parse with v2 parser
        print("\n" + "-"*60)
        print("Parsing with MEMParserV2 (schema-based)...")
        print("-"*60)
        
        parsed = parse_mem_v2(mem_data.encode('utf-8'), control_version=None)
        
        print(f"\n✓ Parsing successful!")
        print(f"\nParsed Results:")
        print(f"  Control Version: {parsed.get('control_version')}")
        print(f"  Program Name: {parsed.get('program_name')}")
        print(f"  Operation Folder Name: {parsed.get('operation_folder_name')}")
        print(f"  Operation Status: {parsed.get('operation_status')}")
        print(f"  Inner Pallet Status: {parsed.get('inner_pallet_status')}")
        print(f"  Spare Tool: {parsed.get('spare_tool')}")
        print(f"  Mode: {parsed.get('mode')}")
        print(f"  Expansion: {parsed.get('expansion')}")
        
        print(f"\nFull parsed data:")
        import json
        print(json.dumps(parsed, indent=2, default=str))
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_posni_schema(ip_address: str = "192.168.86.89", port: int = 10000):
    """Test POSNI schema-based parser."""
    print(f"\n{'='*60}")
    print(f"Testing POSNI Schema Parser on {ip_address}:{port}")
    print(f"{'='*60}\n")
    
    try:
        # Get connection for testing (should be fresh after main() closed existing connection)
        client = await get_or_create_connection(
            ip_address=ip_address,
            port=port,
            timeout=15  # Longer timeout
        )
        
        # Check connection status
        if not client._connected:
            print("Attempting to connect...")
            connected = await client.connect()
            if not connected:
                print("✗ Failed to connect to machine")
                return False
        
        # Fetch POSNI data (assuming machine is set to inches)
        print("Fetching POSNI1 data via Telnet (assuming inches)...")
        posni_data = await client.get_position_data(units='in', verbose=False)
        
        if not posni_data:
            print("✗ Failed to fetch POSNI1 data (may be CM7500 error - machine has data file open)")
            print("  → Close any open data files on the machine and try again")
            return False
        
        print(f"✓ POSNI1 data received ({len(posni_data)} bytes)")
        print(f"\nFirst 500 chars of raw content:")
        print(posni_data[:500])
        
        # Parse with v2 parser
        print("\n" + "-"*60)
        print("Parsing with POSNIParserV2 (schema-based)...")
        print("-"*60)
        
        parsed = parse_posni_v2(posni_data.encode('utf-8'), units='in', control_version=None)
        
        print(f"\n✓ Parsing successful!")
        print(f"\nParsed Results:")
        print(f"  Control Version: {parsed.get('control_version')}")
        print(f"  Units: {parsed.get('units')}")
        
        work_offsets = parsed.get('work_offsets', {})
        print(f"\n  Work Offsets (G54-G59): {len(work_offsets)} found")
        for offset_num in sorted(work_offsets.keys()):
            offset = work_offsets[offset_num]
            print(f"    G{offset_num}: X={offset.get('x')}, Y={offset.get('y')}, Z={offset.get('z')}")
        
        extended_offsets = parsed.get('extended_offsets', {})
        print(f"\n  Extended Offsets (X01-X48/X001-X300): {len(extended_offsets)} found")
        if extended_offsets:
            # Show first 5
            for i, offset_num in enumerate(sorted(extended_offsets.keys())[:5]):
                offset = extended_offsets[offset_num]
                print(f"    X{offset_num:03d}: X={offset.get('x')}, Y={offset.get('y')}, Z={offset.get('z')}")
            if len(extended_offsets) > 5:
                print(f"    ... and {len(extended_offsets) - 5} more")
        
        fixture_offsets = parsed.get('fixture_offsets', {})
        if fixture_offsets:
            print(f"\n  Fixture Offsets (H01): {len(fixture_offsets)} found")
            for offset_num in sorted(fixture_offsets.keys()):
                offset = fixture_offsets[offset_num]
                print(f"    H{offset_num}: X={offset.get('x')}, Y={offset.get('y')}, Z={offset.get('z')}")
        
        rotary_offsets = parsed.get('rotary_offsets', {})
        if rotary_offsets:
            print(f"\n  Rotary Offsets (B01): {len(rotary_offsets)} found")
            for offset_num in sorted(rotary_offsets.keys()):
                offset = rotary_offsets[offset_num]
                print(f"    B{offset_num}: X={offset.get('x')}, Y={offset.get('y')}, Z={offset.get('z')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    ip_address = "192.168.86.89"
    port = 10000
    
    print("="*60)
    print("MEM and POSNI Schema Parser Test")
    print("="*60)
    print("\nNote: This script will close any existing Telnet connection")
    print("      from the Shatter backend (single connection limit per machine).")
    print("      The backend will automatically reconnect when needed.\n")
    print("Note: If tests fail with timeouts, the machine may have")
    print("      a data file open (CM7500 error). Close any open")
    print("      data files on the machine and try again.\n")
    
    # Close any existing connection at the start
    print("Closing any existing Telnet connection from Shatter backend...")
    await close_connection(ip_address, port)
    await asyncio.sleep(0.5)
    
    mem_success = await test_mem_schema()
    posni_success = await test_posni_schema()
    
    # Clean up: close test connection (backend will reconnect when needed)
    print("\nCleaning up test connection...")
    await close_connection(ip_address, port)
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"MEM Schema: {'✓ PASSED' if mem_success else '✗ FAILED'}")
    print(f"POSNI Schema: {'✓ PASSED' if posni_success else '✗ FAILED'}")
    print("="*60)
    print("\nNote: The Shatter backend will automatically reconnect to the")
    print("      machine when it needs to access Telnet data.\n")
    
    return mem_success and posni_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
