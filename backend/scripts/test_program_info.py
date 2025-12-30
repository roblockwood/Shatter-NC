#!/usr/bin/env python3
"""Test script for REDPRGN and REDPRG commands."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.clients.telnet_client import CNCTelnetClient


async def main():
    # Default IP if not provided
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.86.89"
    
    print(f"Testing program information commands on {ip}...")
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
        
        # Test REDPRGN - Get current program info
        print("\n2. Testing REDPRGN (Get current program information)...")
        program_info = await client.get_current_program_info(verbose=True)
        if program_info:
            print("✅ Successfully retrieved program information:")
            print(f"   Currently executed program number: {program_info.get('currently_executed_program_number')}")
            print(f"   Main program number: {program_info.get('main_program_number')}")
            print(f"   Currently executed block number: {program_info.get('currently_executed_block_number')}")
        else:
            print("❌ Failed to get program information")
        
        # Test REDPRG - Get program content
        print("\n3. Testing REDPRG (Get program content by character count)...")
        print("   Requesting 200 characters...")
        program_content = await client.get_current_program_content(character_count=200, verbose=True)
        if program_content:
            print(f"✅ Successfully retrieved program content ({len(program_content)} characters):")
            print("   Content preview:")
            # Show first 100 chars with line breaks for readability
            preview = program_content[:100]
            print(f"   {preview}")
            if len(program_content) > 100:
                print(f"   ... (truncated, total: {len(program_content)} chars)")
        else:
            print("❌ Failed to get program content")
        
        # Test with different character counts
        print("\n4. Testing REDPRG with different character counts...")
        for count in [50, 100, 500]:
            print(f"   Requesting {count} characters...")
            content = await client.get_current_program_content(character_count=count, verbose=False)
            if content:
                print(f"   ✅ Got {len(content)} characters")
            else:
                print(f"   ❌ Failed")
        
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

