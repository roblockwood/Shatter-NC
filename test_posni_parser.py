"""Test POSNI1.NC parser."""
import sys
sys.path.insert(0, 'backend')

from app.parsers.posni_parser import parse_posni, get_work_offset
import json

# Read sample file
with open('Samples/POSNI1.NC', 'rb') as f:
    posni_content = f.read()

# Parse all offsets
result = parse_posni(posni_content)

print("=" * 80)
print("POSNI1.NC PARSER TEST")
print("=" * 80)
print()

print("WORK OFFSETS (G54-G59):")
for offset_num in sorted(result['work_offsets'].keys()):
    offset = result['work_offsets'][offset_num]
    print(f"  G{offset_num}:")
    print(f"    X: {offset['x']:.4f}\"")
    print(f"    Y: {offset['y']:.4f}\"")
    print(f"    Z: {offset['z']:.4f}\"")
    if offset['a'] != 0 or offset['b'] != 0 or offset['c'] != 0:
        print(f"    A: {offset['a']:.3f}° B: {offset['b']:.3f}° C: {offset['c']:.3f}°")
print()

print("EXTENDED OFFSETS (X01-X48):")
active_extended = {k: v for k, v in result['extended_offsets'].items()
                   if v['x'] != 0 or v['y'] != 0 or v['z'] != 0}
if active_extended:
    for offset_num in sorted(active_extended.keys()):
        offset = active_extended[offset_num]
        print(f"  X{offset_num:02d}: X={offset['x']:.4f}\", Y={offset['y']:.4f}\", Z={offset['z']:.4f}\"")
else:
    print(f"  {len(result['extended_offsets'])} extended offsets defined (all zero)")
print()

print("FIXTURE OFFSETS (H01-H99):")
active_fixture = {k: v for k, v in result['fixture_offsets'].items()
                  if v['x'] != 0 or v['y'] != 0 or v['z'] != 0}
if active_fixture:
    for offset_num in sorted(active_fixture.keys()):
        offset = active_fixture[offset_num]
        print(f"  H{offset_num:02d}: X={offset['x']:.4f}\", Y={offset['y']:.4f}\", Z={offset['z']:.4f}\"")
else:
    print(f"  {len(result['fixture_offsets'])} fixture offsets defined (all zero)")
print()

print("ROTARY OFFSETS (B01-B08):")
if result['rotary_offsets']:
    print(f"  {len(result['rotary_offsets'])} rotary offsets defined")
else:
    print("  No rotary offsets")
print()

# Test specific offset lookup
print("=" * 80)
print("TESTING SPECIFIC OFFSET LOOKUP")
print("=" * 80)
print()

test_offset = 54
offset_data = get_work_offset(posni_content, test_offset)
if offset_data:
    print(f"G{test_offset} Offset:")
    print(f"  X: {offset_data['x']:.4f}\"")
    print(f"  Y: {offset_data['y']:.4f}\"")
    print(f"  Z: {offset_data['z']:.4f}\"")
else:
    print(f"G{test_offset} not found")
print()

# Test with validation scenario
print("=" * 80)
print("VALIDATION SCENARIO")
print("=" * 80)
print()
print("Program expects G54: X=-21.9975\", Y=-2.8563\", Z=-15.8976\"")
print("Tolerance: ±0.01\"")
print()

expected = {"x": -21.9975, "y": -2.8563, "z": -15.8976}
actual = get_work_offset(posni_content, 54)
tolerance = 0.01

if actual:
    diff_x = abs(actual['x'] - expected['x'])
    diff_y = abs(actual['y'] - expected['y'])
    diff_z = abs(actual['z'] - expected['z'])

    print(f"Actual G54:")
    print(f"  X: {actual['x']:.4f}\" (diff: {diff_x:.4f}\")")
    print(f"  Y: {actual['y']:.4f}\" (diff: {diff_y:.4f}\")")
    print(f"  Z: {actual['z']:.4f}\" (diff: {diff_z:.4f}\")")
    print()

    within_tolerance = (diff_x <= tolerance and
                        diff_y <= tolerance and
                        diff_z <= tolerance)

    if within_tolerance:
        print("✓ WITHIN TOLERANCE")
    else:
        print("✗ OUTSIDE TOLERANCE")
        if diff_x > tolerance:
            print(f"  X difference {diff_x:.4f}\" exceeds ±{tolerance}\"")
        if diff_y > tolerance:
            print(f"  Y difference {diff_y:.4f}\" exceeds ±{tolerance}\"")
        if diff_z > tolerance:
            print(f"  Z difference {diff_z:.4f}\" exceeds ±{tolerance}\"")

print()
print("=" * 80)
print("JSON OUTPUT:")
print("=" * 80)
print(json.dumps(result, indent=2))
