#!/usr/bin/env python3
"""
Test script for ALARM parser against a live machine.

Tests:
- ALARM data file reading via Telnet
- Control version detection (C00 vs D00)
- Alarm/operator message parsing (E01-E36)
- Loading system alarm parsing (L01-L18)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.clients.telnet_client import get_or_create_connection
from app.parsers.alarm_parser_v2 import parse_alarm_v2


async def test_alarm_parser(ip_address: str, port: int = 10000):
    """Test ALARM parser against live machine."""
    print(f"Testing ALARM parser on {ip_address}:{port}")
    print("=" * 60)
    
    try:
        # Get connection
        print("\n1. Connecting to machine...")
        telnet_client = await get_or_create_connection(
            ip_address=ip_address,
            port=port,
            timeout=15
        )
        print("   ✓ Connected")
        
        # Fetch ALARM data
        print("\n2. Fetching ALARM data...")
        alarm_data = await telnet_client.get_alarm_data(verbose=False)
        
        if not alarm_data:
            print("   ✗ Failed to fetch ALARM data")
            return False
        
        print(f"   ✓ Received {len(alarm_data)} bytes of ALARM data")
        print(f"\n   Raw data preview (first 200 chars):")
        print(f"   {repr(alarm_data[:200])}")
        
        # Parse ALARM data
        print("\n3. Parsing ALARM data...")
        parsed = parse_alarm_v2(alarm_data.encode('utf-8'), control_version=None)
        
        print(f"   ✓ Control version detected: {parsed.get('control_version')}")
        
        # Display alarms
        alarms = parsed.get("alarms", [])
        loading_alarms = parsed.get("loading_alarms", [])
        
        print(f"\n4. Alarm/Operator Messages (E01-E36): {len(alarms)} found")
        if alarms:
            for i, alarm in enumerate(alarms[:10], 1):  # Show first 10
                print(f"   {i}. Code: {alarm.get('code')}")
                print(f"      Category: {alarm.get('category')} ({alarm.get('category_code')})")
                print(f"      Number: {alarm.get('number')}")
                print(f"      Auxiliary: {alarm.get('auxiliary')}")
                print(f"      Type: {alarm.get('type')}")
                description = alarm.get('description', '')
                if description:
                    print(f"      Description: {description}")
                solution = alarm.get('solution', '')
                if solution:
                    # Show first 100 chars of solution
                    solution_preview = solution[:100] + ('...' if len(solution) > 100 else '')
                    print(f"      Solution: {solution_preview}")
            if len(alarms) > 10:
                print(f"   ... and {len(alarms) - 10} more")
        else:
            print("   (No alarms/operator messages)")
        
        print(f"\n5. Loading System Alarms (L01-L18): {len(loading_alarms)} found")
        if loading_alarms:
            for i, alarm in enumerate(loading_alarms[:10], 1):  # Show first 10
                print(f"   {i}. Code: {alarm.get('code')}")
                print(f"      Category: {alarm.get('category')}")
                print(f"      Number: {alarm.get('number')}")
                print(f"      Auxiliary: {alarm.get('auxiliary')}")
            if len(loading_alarms) > 10:
                print(f"   ... and {len(loading_alarms) - 10} more")
        else:
            print("   (No loading system alarms)")
        
        # Summary
        print("\n" + "=" * 60)
        print("✓ ALARM parser test completed successfully")
        print(f"  - Control version: {parsed.get('control_version')}")
        print(f"  - Total alarms/operator messages: {len(alarms)}")
        print(f"  - Total loading system alarms: {len(loading_alarms)}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up connection
        from app.clients.telnet_client import close_connection
        print("\n6. Cleaning up connection...")
        await close_connection(ip_address, port)
        print("   ✓ Connection closed")


async def main():
    """Main test function."""
    # Default test machine
    ip_address = "192.168.86.89"
    port = 10000
    
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    success = await test_alarm_parser(ip_address, port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

