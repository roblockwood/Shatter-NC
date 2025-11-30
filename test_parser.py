"""Test G-code parser against sample file."""
import sys
sys.path.insert(0, 'backend')

from app.parsers.gcode_parser import parse_gcode
import json

# Read sample file
with open('Samples/S700 ORANGE VISE 2-OP_OP1.NC', 'r') as f:
    gcode_content = f.read()

# Parse
result = parse_gcode(gcode_content)

# Pretty print results
print("=" * 80)
print("G-CODE PARSER TEST RESULTS")
print("=" * 80)
print()

print("POSTED DATE:")
print(f"  {result['posted_date']}")
print()

print("TOOLS:")
for tool in result['tools']:
    print(f"  T{tool['tool_number']:02d}:")
    print(f"    Diameter: {tool['diameter']}\"")
    print(f"    Corner Radius: {tool['corner_radius']}\"")
    print(f"    Length: {tool['length_used']:.4f}\" used / {tool['length_total']:.4f}\" total")
    print(f"    Description: {tool['description']}")
    print()

print("STOCK SIZE:")
if result['stock_size']:
    print(f"  X: {result['stock_size']['x']}\"")
    print(f"  Y: {result['stock_size']['y']}\"")
    print(f"  Z: {result['stock_size']['z']}\"")
else:
    print("  Not found")
print()

print("WCS LOCATION:")
if result['wcs_location']:
    for axis, values in result['wcs_location'].items():
        print(f"  {axis.upper()}: MIN {values['min']:.4f}\" MAX {values['max']:.4f}\"")
else:
    print("  Not found")
print()

print("FILE STATISTICS:")
print(f"  Line count: {result['line_count']:,}")
print(f"  File size: {result['file_size']:,} bytes")
print()

print("ESTIMATED RUNTIME:")
minutes = int(result['estimated_runtime_seconds'] // 60)
seconds = int(result['estimated_runtime_seconds'] % 60)
print(f"  {minutes:02d}:{seconds:02d} ({result['estimated_runtime_seconds']:.1f} seconds)")
print()

print("=" * 80)
print("JSON OUTPUT:")
print("=" * 80)
print(json.dumps(result, indent=2, default=str))
