#!/usr/bin/env python3
"""Standalone script to detect protocols on a CNC machine.

Usage:
    python detect_protocols.py <ip_address>
    python detect_protocols.py 192.168.1.100
"""
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.protocol_detector import detect_protocols
from app.clients.http_client import CNCHttpClient
from app.clients.ftp_client import CNCFtpClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python detect_protocols.py <ip_address> [http_port] [ftp_port]")
        print("Example: python detect_protocols.py 192.168.1.100 80 21")
        sys.exit(1)

    ip_address = sys.argv[1]
    http_port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    ftp_port = int(sys.argv[3]) if len(sys.argv) > 3 else 21

    print(f"Detecting protocols on {ip_address}...")
    print(f"HTTP port: {http_port}, FTP port: {ftp_port}")
    print("-" * 60)

    # Initialize clients
    http_client = None
    ftp_client = None

    try:
        http_client = CNCHttpClient(ip_address, port=http_port, timeout=5)
        print("✓ HTTP client initialized")
    except Exception as e:
        print(f"✗ Could not initialize HTTP client: {e}")

    try:
        ftp_client = CNCFtpClient(
            ip_address=ip_address,
            port=ftp_port,
            username="anonymous",
            password="anonymous",
            timeout=10,
        )
        print("✓ FTP client initialized")
    except Exception as e:
        print(f"✗ Could not initialize FTP client: {e}")

    print("-" * 60)

    # Run detection
    try:
        results = await detect_protocols(
            ip_address=ip_address,
            http_port=http_port,
            ftp_client=ftp_client,
            http_client=http_client,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("PROTOCOL DETECTION RESULTS")
        print("=" * 60)

        # FOCAS
        print("\n📡 FOCAS Detection:")
        focas_available = results["summary"]["focas_available"]
        if focas_available:
            print("  ✓ FOCAS appears to be AVAILABLE!")
            for result in results["focas"]["results"]:
                if result["open"]:
                    print(f"    - Port {result['port']}: OPEN")
                    if result.get("protocol"):
                        print(f"      Protocol: {result['protocol']}")
                    if result.get("banner"):
                        print(f"      Banner: {result['banner'][:50]}")
        else:
            print("  ✗ FOCAS not detected")
            print("    Checked ports:", ", ".join(map(str, results["focas"]["ports_checked"])))

        # Other protocols
        print("\n📡 Other Protocols:")
        if results["summary"]["other_protocols"]:
            for proto in results["summary"]["other_protocols"]:
                print(f"  ✓ {proto['name']} on port {proto['port']}")
                if proto.get("banner"):
                    print(f"    Banner: {proto['banner'][:50]}")
        else:
            print("  No other common protocols detected")

        # System files
        if "system_files" in results and results["system_files"].get("hints"):
            print("\n📄 System File Hints:")
            for hint in results["system_files"]["hints"]:
                print(f"  - {hint}")

        # HTTP endpoints
        if "http_endpoints" in results and results["http_endpoints"].get("protocol_hints"):
            print("\n🌐 HTTP Endpoint Hints:")
            for hint in results["http_endpoints"]["protocol_hints"]:
                print(f"  - {hint}")

        # Recommendations
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)

        if focas_available:
            print("\n✓ FOCAS is available! You can:")
            print("  - Install FOCAS library (Fwlib32.dll on Windows, libfwlib32.so on Linux)")
            print("  - Use FOCAS API for real-time position, control, and advanced features")
            print("  - Get current XYZ position, spindle speed, feedrate, etc.")
            print("  - Control machine operations programmatically")

        if not focas_available:
            print("\n⚠ No advanced protocols detected.")
            print("  Current capabilities:")
            print("    - HTTP endpoints for status monitoring")
            print("    - FTP for file transfer and system files")
            print("  To enable more functionality:")
            print("    - Check machine configuration for FOCAS options")
            print("    - Consult machine manual for protocol setup")
            print("    - Contact machine manufacturer for protocol availability")

        # Save full results to JSON
        output_file = f"protocol_detection_{ip_address.replace('.', '_')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Full results saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

