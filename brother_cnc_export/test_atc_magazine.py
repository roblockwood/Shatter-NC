#!/usr/bin/env python3
"""
Test ATC magazine reading with ATCTL parser

This script tests all ATC-related methods:
- read_atc_magazine(): Full magazine configuration
- get_spindle_tool(): Tool in spindle
- get_pot_tool(): Tool in specific pot
- list_empty_pots(): All empty positions
- list_assigned_tools(): All assigned tool-position mappings
"""

from brother_cnc_client import BrotherCNCClient

def test_read_atc_magazine():
    """Test reading ATC magazine configuration."""
    print("Testing ATC Magazine Operations\n" + "=" * 60)

    client = BrotherCNCClient()
    client.connect()

    try:
        # Test 1: Read full magazine
        print("\n[TEST 1] Reading full ATC magazine configuration...")
        magazine = client.read_atc_magazine()

        if not magazine:
            print("✗ Failed to read ATC magazine")
            return False

        print(f"✓ Successfully read {len(magazine)} magazine positions\n")

        # Display spindle
        if 0 in magazine:
            spindle = magazine[0]
            print(f"SPINDLE (M01):")
            print(f"  Tool #: {spindle['tool_num']}")
            print(f"  Type: {spindle['type']}")
            print(f"  Mode: {spindle['nc_mode']}")
            print(f"  Group: {spindle['group']}")
            print(f"  Color: {spindle['color']}\n")

        # Display specific pot (Pot 10 = position 10)
        if 10 in magazine:
            pot_10 = magazine[10]
            print(f"POT 10 (M11):")
            print(f"  Tool #: {pot_10['tool_num']}")
            print(f"  Type: {pot_10['type']}")
            print(f"  Mode: {pot_10['nc_mode']}")
            print(f"  Group: {pot_10['group']}")
            print(f"  Color: {pot_10['color']}\n")

        # Show summary
        print("Magazine Summary:")
        print("-" * 60)
        tool_count = sum(1 for pos in magazine.values() if pos['tool_num_set'])
        print(f"Total tools assigned: {tool_count}")

        empty_pots = [pos for pos, data in magazine.items()
                     if pos > 0 and not data['tool_num_set']]
        print(f"Empty pots: {len(empty_pots)}")

        # List first few tools
        print("\nFirst 5 positions:")
        for pos in range(min(5, 51)):
            if pos in magazine:
                data = magazine[pos]
                pos_name = "SPINDLE" if pos == 0 else f"POT {pos}"
                tool_str = f"Tool #{data['tool_num']}" if data['tool_num_set'] else "Empty"
                print(f"  {pos_name:12} {tool_str}")

        # Test 2: Get spindle tool
        print("\n\n[TEST 2] Getting spindle tool...")
        spindle_tool = client.get_spindle_tool()
        if spindle_tool:
            print(f"✓ Spindle contains: Tool #{spindle_tool['tool_num']} ({spindle_tool['type']})")
        else:
            print("✓ Spindle is empty (as expected)")

        # Test 3: Get pot 10 tool (should have tool #24)
        print("\n[TEST 3] Getting tool in pot 10...")
        pot_10_tool = client.get_pot_tool(10)
        if pot_10_tool:
            print(f"✓ Pot 10 contains: Tool #{pot_10_tool['tool_num']} ({pot_10_tool['type']})")
            # Verify it matches what we got earlier
            if pot_10_tool['tool_num'] == 24:
                print("✓ Verified: Tool #24 is in pot 10")
            else:
                print(f"✗ Expected tool #24, got tool #{pot_10_tool['tool_num']}")
                return False
        else:
            print("✗ Pot 10 is empty (unexpected)")
            return False

        # Test 4: List empty pots
        print("\n[TEST 4] Listing empty pots...")
        empty = client.list_empty_pots()
        if empty:
            print(f"✓ Found {len(empty)} empty pots")
            print(f"  Empty pots: {empty[:10]}..." if len(empty) > 10 else f"  Empty pots: {empty}")
        else:
            print("✓ No empty pots (all assigned)")

        # Test 5: List assigned tools
        print("\n[TEST 5] Listing all assigned tools...")
        assigned = client.list_assigned_tools()
        if assigned:
            print(f"✓ Found {len(assigned)} assigned tools")
            # Show first 5
            for pos in sorted(assigned.keys())[:5]:
                if pos == 0:
                    print(f"  Spindle: Tool #{assigned[pos]}")
                else:
                    print(f"  Pot {pos}: Tool #{assigned[pos]}")
        else:
            print("✗ No assigned tools found (unexpected)")
            return False

        print("\n" + "=" * 60)
        print("✓ All ATC Magazine Tests PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        client.disconnect()

if __name__ == "__main__":
    success = test_read_atc_magazine()
    exit(0 if success else 1)
