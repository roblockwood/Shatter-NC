#!/usr/bin/env python3
"""
Test script for MONTR parser against live machine.

This script tests the MONTR schema and parser implementation by:
1. Fetching MONTR data from the machine via Telnet
2. Parsing the data with control version detection
3. Displaying the parsed results
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.clients.telnet_client import get_or_create_connection, close_connection
from app.parsers.montr_parser_v2 import parse_montr_v2


async def test_montr(ip_address: str, port: int = 10000):
    """Test MONTR data fetching and parsing."""
    print(f"Testing MONTR parser against {ip_address}:{port}")
    print("=" * 60)
    
    try:
        # Close any existing connection (per machine testing skill)
        print("\n1. Closing any existing Telnet connection...")
        await close_connection(ip_address, port)
        await asyncio.sleep(0.5)
        
        # Create fresh connection for testing
        print("2. Creating fresh Telnet connection...")
        telnet_client = await get_or_create_connection(
            ip_address=ip_address,
            port=port,
            timeout=15
        )
        
        if not telnet_client:
            print("ERROR: Failed to create Telnet client instance")
            return False
        
        # Ensure connection is established
        if not telnet_client._connected:
            print("   Attempting to connect...")
            connected = await telnet_client.connect()
            if not connected:
                print("ERROR: Failed to establish Telnet connection")
                print("   This may indicate:")
                print("   - Machine is busy (CM7500: editing communication data)")
                print("   - Telnet port 10000 is blocked")
                print("   - Machine is offline")
                return False
        
        print("   ✓ Connection established")
        
        # Fetch MONTR data
        print("\n3. Fetching MONTR data...")
        montr_data = await telnet_client.get_monitor_data(verbose=True)
        
        if montr_data is None:
            print("ERROR: Failed to fetch MONTR data")
            print("   This could mean:")
            print("   - MONTR file doesn't exist on this machine")
            print("   - Machine is busy (CM7500: editing communication data)")
            print("   - Command format issue")
            return False
        
        print(f"   ✓ Received {len(montr_data)} bytes of MONTR data")
        print("\n   Raw MONTR data (first 500 chars):")
        print("   " + "-" * 56)
        print(f"   {repr(montr_data[:500])}")
        print("   " + "-" * 56)
        
        # Parse MONTR data
        print("\n4. Parsing MONTR data...")
        parsed = parse_montr_v2(montr_data.encode('utf-8'), control_version=None)
        
        print(f"   ✓ Control version detected: {parsed.get('control_version', 'UNKNOWN')}")
        
        # Display parsed results
        print("\n5. Parsed Results:")
        print("   " + "=" * 56)
        
        # Program Info
        program_info = parsed.get("program_info", {})
        print("\n   Program Information:")
        print(f"     Operation Program: {program_info.get('operation_program_no', 'N/A')}")
        print(f"     Edit Program:      {program_info.get('edit_program_no', 'N/A')}")
        print(f"     Operation Folder:  {program_info.get('operation_folder_name', 'N/A')[:50]}...")
        print(f"     Edit Folder:       {program_info.get('edit_folder_name', 'N/A')[:50]}...")
        
        # Time Info
        time_info = parsed.get("time_info", {})
        print("\n   Time Information:")
        print(f"     Total Operation Time: {time_info.get('total_operation_time', 'N/A')}")
        print(f"     Power On Time:        {time_info.get('power_on_time', 'N/A')}")
        print(f"     Operation Time:        {time_info.get('operation_time', 'N/A')}")
        
        # Counters
        counters = parsed.get("counters", [])
        print(f"\n   Workpiece Counters ({len(counters)} found):")
        for counter in counters:
            counter_num = counter.get("counter_number", "?")
            count = counter.get("count", 0)
            current = counter.get("current", 0)
            end = counter.get("end", 0)
            end_warning = counter.get("end_warning", 0)
            print(f"     Counter {counter_num}: count={count}, current={current}, end={end}, end_warning={end_warning}")
        
        print("\n   " + "=" * 56)
        print("\n✓ MONTR test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up: close test connection
        print("\n6. Cleaning up test connection...")
        await close_connection(ip_address, port)
        print("   ✓ Connection closed")
        print("\n   Note: Backend will automatically reconnect when needed.")


if __name__ == "__main__":
    ip_address = "192.168.86.89"
    port = 10000
    
    print("\n" + "=" * 60)
    print("MONTR Parser Test")
    print("=" * 60)
    
    success = asyncio.run(test_montr(ip_address, port))
    
    sys.exit(0 if success else 1)

