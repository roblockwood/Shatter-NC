"""Test the program validation endpoint."""
import requests
import json

# Read sample G-code
with open('Samples/S700 ORANGE VISE 2-OP_OP1.NC', 'r') as f:
    gcode_content = f.read()

# Prepare request
machine_id = 2  # Assuming Speedio machine exists in database
url = f"http://localhost:8000/api/machines/{machine_id}/programs/validate"

payload = {
    "gcode_content": gcode_content
}

print("=" * 80)
print("TESTING PROGRAM VALIDATION ENDPOINT")
print("=" * 80)
print(f"\nEndpoint: POST {url}")
print(f"Machine ID: {machine_id}")
print(f"Program: ORANGE VISE 2-OP_OP1.NC")
print(f"File size: {len(gcode_content):,} bytes")
print("\nSending request...")

try:
    response = requests.post(url, json=payload, timeout=30)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\n" + "=" * 80)
        print("VALIDATION RESULT")
        print("=" * 80)
        print(f"\nValid: {result['valid']}")
        print(f"\nMetadata:")
        print(f"  Posted Date: {result['metadata']['posted_date']}")
        print(f"  Estimated Runtime: {result['metadata']['estimated_runtime_seconds']:.1f}s ({result['metadata']['estimated_runtime_seconds']//60:.0f}m {result['metadata']['estimated_runtime_seconds']%60:.0f}s)")
        print(f"  Tool Count: {result['metadata']['tool_count']}")
        print(f"  Line Count: {result['metadata']['line_count']:,}")

        print(f"\nTools Validation:")
        for tool_num, tool_result in result['tools'].items():
            print(f"  T{int(tool_num):02d}:")
            print(f"    Required: D={tool_result['required_diameter']}\", CR={tool_result['required_corner_radius']}\", L={tool_result['required_length']:.4f}\"")
            print(f"    Available: {tool_result['available']}")
            print(f"    Matches: Diameter={tool_result['diameter_match']}, CR={tool_result['corner_radius_match']}, Length={tool_result['length_sufficient']}")
            if tool_result['warnings']:
                print(f"    Warnings: {', '.join(tool_result['warnings'])}")

        if result['wcs_offset']:
            wcs = result['wcs_offset']
            print(f"\nWCS Offset Validation:")
            print(f"  Work Offset: G{wcs['work_offset']}")
            print(f"  Expected: X={wcs['expected']['x']:.4f}\", Y={wcs['expected']['y']:.4f}\", Z={wcs['expected']['z']:.4f}\"")
            print(f"  Tolerance: ±{wcs['tolerance']:.4f}\"")
            print(f"  Within Tolerance: {wcs['within_tolerance']}")
            if wcs['warnings']:
                print(f"  Warnings: {', '.join(wcs['warnings'])}")

        if result['warnings']:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")

        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  ❌ {error}")

        print("\n" + "=" * 80)
        print("JSON RESPONSE:")
        print("=" * 80)
        print(json.dumps(result, indent=2))

    else:
        print(f"\n❌ Request failed:")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to server. Is it running?")
    print("   Start with: uvicorn app.main:app --reload")
except Exception as e:
    print(f"\n❌ Error: {e}")
