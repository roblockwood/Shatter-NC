#!/usr/bin/env python3
"""Test script for control type detection (C00 vs D00)."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.clients.telnet_client import CNCTelnetClient


async def main():
    # Default IP if not provided
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.86.89"
    
    print(f"Testing control type detection on {ip}...")
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
        
        # Test control type detection
        print("\n2. Testing control type detection...")
        print("   (Verbose mode enabled to show all indicators)")
        control_type = await client.detect_control_type(verbose=True)
        
        if control_type:
            print(f"✅ Control type detected: {control_type}")
        else:
            print("❌ Could not determine control type")
            
            # Show directory listing for debugging
            print("\n3. Showing directory listing for debugging...")
            directory_data = await client.get_directory_listing(verbose=False)
            if directory_data:
                entries = await client.parse_directory_listing(directory_data)
                if entries:
                    print(f"   Found {len(entries)} files in directory:")
                    # Show files that might be relevant
                    for entry in entries[:20]:  # Show first 20
                        name = entry.get('name', '')
                        if 'PRDC' in name or 'PRDD' in name or 'SYSC' in name or 'SYSD' in name:
                            print(f"   - {name} (size: {entry.get('size')})")
                    if len(entries) > 20:
                        print(f"   ... and {len(entries) - 20} more files")
        
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

