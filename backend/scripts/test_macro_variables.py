#!/usr/bin/env python3
"""Test script for REDMCNM macro variable commands."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.clients.telnet_client import CNCTelnetClient


async def main():
    # Default IP if not provided
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    
    print(f"Testing macro variable commands on {ip}...")
    print("=" * 60)
    
    client = CNCTelnetClient(ip_address=ip)
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        result = await client.test_connection()
        if not result.get("success"):
            print(f"❌ Connection failed: {result.get('error')}")
            return
        print(f"✅ Connection successful (latency: {result.get('latency_ms')}ms)")
        
        # Test REDMCNM - Get macro variable #302 (units)
        print("\n2. Testing REDMCNM (Get macro variable #302 - Units)...")
        units = await client.get_units(verbose=True)
        if units:
            print(f"✅ Machine units: {units}")
            print(f"   (0 = metric/mm, 1 = imperial/inch)")
        else:
            print("❌ Failed to get units")
        
        # Test REDMCNM - Get a few other macro variables
        print("\n3. Testing REDMCNM (Get other macro variables)...")
        for macro_num in [500, 501, 502]:
            value = await client.get_macro_variable(macro_num, verbose=False)
            if value is not None:
                print(f"   Macro #{macro_num}: {value}")
            else:
                print(f"   Macro #{macro_num}: Failed")
        
        # Test REDMCNM range - Get range of macro variables
        print("\n4. Testing REDMCNM range (Get macro variables 500-504)...")
        values = await client.get_macro_variable_range(500, 5, verbose=True)
        if values:
            print(f"✅ Retrieved {len(values)} macro variables:")
            for i, value in enumerate(values):
                print(f"   Macro #{500 + i}: {value}")
        else:
            print("❌ Failed to get macro variable range")
        
        # Test other RED commands
        print("\n5. Testing REDDATE (Get date/time)...")
        date_time = await client.get_date_time(verbose=True)
        if date_time:
            print(f"✅ Machine date/time: {date_time}")
            if len(date_time) == 14:
                print(f"   Formatted: {date_time[0:4]}-{date_time[4:6]}-{date_time[6:8]} {date_time[8:10]}:{date_time[10:12]}:{date_time[12:14]}")
        else:
            print("❌ Failed to get date/time")
        
        print("\n6. Testing REDFILE (Get file control data)...")
        file_data = await client.get_file_control_data(verbose=True)
        if file_data:
            print(f"✅ File control data:")
            print(f"   Registrations: {file_data.get('number_of_registrations')}")
            print(f"   Possible registrations: {file_data.get('number_of_possible_registrations')}")
            print(f"   Memory usage: {file_data.get('memory_usage')} bytes")
            print(f"   Remaining memory: {file_data.get('remaining_memory')} bytes")
        else:
            print("❌ Failed to get file control data")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n" + "=" * 60)
        print("Test completed.")


if __name__ == "__main__":
    asyncio.run(main())

