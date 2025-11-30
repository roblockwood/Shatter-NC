"""FTP client for file operations with Brother CNC machines."""
import aioftp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class CNCFtpClient:
    """Async FTP client for Brother CNC file operations."""

    def __init__(
        self,
        ip_address: str,
        port: int = 21,
        username: str = "anonymous",
        password: str = "anonymous",
        timeout: int = 10,
    ):
        """
        Initialize FTP client.

        Args:
            ip_address: CNC machine IP address
            port: FTP port (default 21)
            username: FTP username
            password: FTP password
            timeout: Connection timeout in seconds
        """
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test FTP connection.

        Returns:
            Dict with connection test results
        """
        try:
            start_time = datetime.now()
            async with aioftp.Client.context(
                self.ip_address,
                port=self.port,
                user=self.username,
                password=self.password,
            ) as client:
                # Try to get current directory to verify connection
                await client.get_current_directory()
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds() * 1000

                return {
                    "success": True,
                    "latency_ms": round(latency, 2),
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"FTP connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def list_files(self, path: str = "/") -> List[Dict[str, Any]]:
        """
        List files in CNC directory.

        Args:
            path: Directory path (default root)

        Returns:
            List of file information dicts
        """
        try:
            async with aioftp.Client.context(
                self.ip_address,
                port=self.port,
                user=self.username,
                password=self.password,
            ) as client:
                files = []
                async for path_obj, info in client.list(path):
                    file_info = {
                        "name": path_obj.name,
                        "path": str(path_obj),
                        "is_directory": info.get("type") == "dir",
                        "size": info.get("size", 0),
                        "modified": info.get("modify", ""),
                    }
                    files.append(file_info)

                return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    async def download_file(self, remote_path: str) -> Optional[bytes]:
        """
        Download file from CNC.

        Args:
            remote_path: Path to file on CNC (e.g., 'O2000.NC')

        Returns:
            File contents as bytes, or None on error
        """
        try:
            async with aioftp.Client.context(
                self.ip_address,
                port=self.port,
                user=self.username,
                password=self.password,
            ) as client:
                # Download to memory buffer
                buffer = BytesIO()
                await client.download_stream(remote_path, buffer)
                return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return None

    async def upload_file(
        self, local_content: bytes, remote_path: str
    ) -> Dict[str, Any]:
        """
        Upload file to CNC.

        Args:
            local_content: File content as bytes
            remote_path: Destination path on CNC (e.g., 'O2000.NC')

        Returns:
            Upload result dict
        """
        try:
            async with aioftp.Client.context(
                self.ip_address,
                port=self.port,
                user=self.username,
                password=self.password,
            ) as client:
                # Upload from memory buffer
                buffer = BytesIO(local_content)
                await client.upload_stream(buffer, remote_path)

                return {
                    "success": True,
                    "remote_path": remote_path,
                    "size": len(local_content),
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error uploading to {remote_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """
        Delete file from CNC.

        Args:
            remote_path: Path to file on CNC

        Returns:
            Deletion result dict
        """
        try:
            async with aioftp.Client.context(
                self.ip_address,
                port=self.port,
                user=self.username,
                password=self.password,
            ) as client:
                await client.remove(remote_path)

                return {
                    "success": True,
                    "remote_path": remote_path,
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error deleting {remote_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_system_file(self, filename: str) -> Optional[str]:
        """
        Download and decode a system file (like ALARM.NC, MONTR.NC).

        Args:
            filename: System file name (e.g., 'ALARM.NC')

        Returns:
            File contents as string, or None on error
        """
        content = await self.download_file(filename)
        if content:
            try:
                return content.decode("utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Error decoding {filename}: {e}")
                return None
        return None

    async def get_programs(self) -> List[Dict[str, Any]]:
        """
        Get list of NC programs (O-numbers and user programs).

        Returns:
            List of program files with metadata
        """
        all_files = await self.list_files("/")

        # Filter for NC programs (O-numbers)
        programs = []
        for file_info in all_files:
            name = file_info["name"]
            # Match O-number files (O####.NC)
            if name.startswith("O") and name.endswith(".NC"):
                # Try to extract O-number
                try:
                    o_number = int(name[1:-3])  # Remove 'O' and '.NC'
                    file_info["o_number"] = o_number
                    file_info["is_user_program"] = 2000 <= o_number <= 3999
                    programs.append(file_info)
                except ValueError:
                    # Not a valid O-number, skip
                    pass

        # Sort by O-number
        programs.sort(key=lambda x: x.get("o_number", 0))
        return programs

    async def get_alarm_data(self) -> Optional[str]:
        """
        Get current alarm data from ALARM.NC system file.

        Returns:
            Alarm data as string
        """
        return await self.get_system_file("ALARM.NC")

    async def get_position_data(self) -> Optional[str]:
        """
        Get current position data from POSNI1.NC system file.

        Returns:
            Position data as string
        """
        return await self.get_system_file("POSNI1.NC")

    async def get_monitor_data(self) -> Optional[str]:
        """
        Get monitor data from MONTR.NC system file.

        Returns:
            Monitor data as string
        """
        return await self.get_system_file("MONTR.NC")


# Helper function for sync usage
def run_async(coro):
    """Helper to run async function in sync context."""
    try:
        loop = asyncio.get_running_loop()
        # Already in async context
        return coro
    except RuntimeError:
        # Not in async context, create new loop
        return asyncio.run(coro)
