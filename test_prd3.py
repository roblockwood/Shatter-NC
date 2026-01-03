#!/usr/bin/env python3
"""
Test script for PRD3/PRDD3 parser against live machine.

This script:
1. Connects to the machine via Telnet
2. Fetches PRD3/PRDD3 data
3. Parses and displays the status information
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.clients.telnet_client import CNCTelnetClient, close_connection
from app.parsers.prd3_parser_v2 import parse_prd3_v2


async def test_prd3(ip_address: str, port: int = 10000):
    """Test PRD3 parsing on live machine."""
    print(f"Testing PRD3 parsing on {ip_address}:{port}")
    print("=" * 60)
    
    client = None
    try:
        # Create client
        client = CNCTelnetClient(ip_address, port, timeout=10)
        
        # Connect
        print("\n1. Connecting to machine...")
        await client.connect()
        print("   ✓ Connected")
        
        # Detect control version
        print("\n2. Detecting control version...")
        control_version = await client.detect_control_type()
        print(f"   ✓ Control version: {control_version}")
        
        # Determine data name
        data_name = "PRDD3" if control_version == "D00" else "PRD3"
        print(f"   ✓ Using data file: {data_name}")
        
        # Fetch PRD3 data
        print(f"\n3. Fetching {data_name} data...")
        prd3_data = await client.get_prd3_data(control_version=control_version, verbose=True)
        
        if not prd3_data:
            print("   ✗ Failed to fetch PRD3 data")
            return
        
        print(f"   ✓ Received {len(prd3_data)} bytes")
        print(f"\n   Raw data (first 500 chars):")
        print(f"   {repr(prd3_data[:500])}")
        
        # Parse PRD3 data
        print(f"\n4. Parsing {data_name} data...")
        prd3_parsed = parse_prd3_v2(prd3_data.encode('utf-8'), control_version=control_version)
        
        print(f"   ✓ Parsed successfully")
        print(f"\n   Parsed data structure:")
        print(f"   {prd3_parsed}")
        
        # Display header info
        header = prd3_parsed.get("header", {})
        print(f"\n5. Header (A01 line):")
        for key, value in header.items():
            print(f"   {key}: {value}")
        
        # Display current status
        current_status = prd3_parsed.get("current_status", {})
        print(f"\n6. Current Status (C01 line):")
        if current_status:
            status_code = current_status.get("current_status")
            status_string = current_status.get("status")
            print(f"   Status Code (raw): {status_code}")
            print(f"   Status (mapped): {status_string}")
            print(f"   Start Date/Time: {current_status.get('start_date_time', 'N/A')}")
            print(f"   Language: {current_status.get('current_language', 'N/A')} (0=NC, 1=Conversation)")
            print(f"   Program/Error No.: {current_status.get('program_or_error_no', 'N/A')}")
            print(f"   Folder Name: {current_status.get('folder_name', 'N/A')}")
            print(f"   Memory Operation Type: {current_status.get('memory_operation_type', 'N/A')}")
            
            # Status code mapping explanation
            print(f"\n7. Status Code Mapping:")
            status_map = {
                1: "Power OFF",
                2: "Standby mode",
                3: "Operating",
                4: "Stopped",
                5: "Error"
            }
            for code, desc in status_map.items():
                marker = " <-- CURRENT" if code == status_code else ""
                print(f"   {code}: {desc}{marker}")
        else:
            print("   ✗ No current status data found")
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if client:
            await client.disconnect()
            print("\n✓ Disconnected")
    
    return 0


if __name__ == "__main__":
    # Default to test machine
    ip_address = "192.168.86.89"
    port = 10000
    
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    exit_code = asyncio.run(test_prd3(ip_address, port))
    sys.exit(exit_code)

