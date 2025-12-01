"""FTP client for file operations with Brother CNC machines."""
import asyncio
from ftplib import FTP, error_perm
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from io import BytesIO
import re

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
        Test FTP connection using active mode.

        Returns:
            Dict with connection test results
        """
        def _test_sync():
            ftp = None
            try:
                start_time = datetime.now()
                ftp = FTP()
                ftp.set_pasv(False)  # Use ACTIVE mode
                ftp.connect(self.ip_address, self.port, timeout=self.timeout)
                ftp.login(self.username, self.password)
                ftp.pwd()  # Get current directory to verify connection
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds() * 1000
                ftp.quit()
                return latency
            except Exception as e:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
                raise e

        try:
            loop = asyncio.get_event_loop()
            latency = await asyncio.wait_for(
                loop.run_in_executor(None, _test_sync),
                timeout=self.timeout
            )
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
        List files in CNC directory using active FTP mode.

        Args:
            path: Directory path (default root)

        Returns:
            List of file information dicts
        """
        def _list_files_sync():
            """Synchronous FTP operations to run in thread pool."""
            ftp = None
            try:
                ftp = FTP()
                ftp.set_pasv(False)  # Use ACTIVE mode
                ftp.connect(self.ip_address, self.port, timeout=self.timeout)
                ftp.login(self.username, self.password)

                files = []
                # Use MLSD if available (provides structured data)
                try:
                    for name, facts in ftp.mlsd(path):
                        if name in ('.', '..'):
                            continue
                        files.append({
                            "name": name,
                            "path": f"{path}/{name}".replace("//", "/"),
                            "is_directory": facts.get("type") == "dir",
                            "size": int(facts.get("size", 0)),
                            "modified": facts.get("modify", ""),
                        })
                except:
                    # Fallback to NLST + SIZE for basic servers
                    file_list = ftp.nlst(path) if path != "/" else ftp.nlst()
                    for name in file_list:
                        try:
                            size = ftp.size(name)
                        except:
                            size = 0
                        files.append({
                            "name": name,
                            "path": f"/{name}",
                            "is_directory": False,
                            "size": size,
                            "modified": "",
                        })

                ftp.quit()
                return files

            except Exception as e:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
                raise e

        try:
            # Run synchronous FTP in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            files = await asyncio.wait_for(
                loop.run_in_executor(None, _list_files_sync),
                timeout=self.timeout
            )
            return files

        except asyncio.TimeoutError:
            logger.error(f"Timeout listing files on {self.ip_address}")
            raise Exception(f"FTP connection timeout after {self.timeout} seconds")
        except ConnectionResetError:
            logger.error(f"FTP connection reset by {self.ip_address}")
            raise Exception("FTP server connection reset - server may be busy or offline")
        except Exception as e:
            logger.error(f"Error listing files from {self.ip_address}: {type(e).__name__}: {e}")
            raise Exception(f"FTP error: {type(e).__name__}: {str(e)}")

    async def download_file(self, remote_path: str) -> Optional[bytes]:
        """
        Download file from CNC using active FTP mode.

        Args:
            remote_path: Path to file on CNC (e.g., 'O2000.NC')

        Returns:
            File contents as bytes, or None on error
        """
        def _download_sync():
            ftp = None
            try:
                ftp = FTP()
                ftp.set_pasv(False)  # Use ACTIVE mode
                ftp.connect(self.ip_address, self.port, timeout=self.timeout)
                ftp.login(self.username, self.password)

                buffer = BytesIO()
                ftp.retrbinary(f'RETR {remote_path}', buffer.write)
                ftp.quit()
                return buffer.getvalue()

            except Exception as e:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
                raise e

        try:
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, _download_sync),
                timeout=self.timeout
            )
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return None

    async def upload_file(
        self, local_content: bytes, remote_path: str
    ) -> Dict[str, Any]:
        """
        Upload file to CNC using active FTP mode.

        Args:
            local_content: File content as bytes
            remote_path: Destination path on CNC (e.g., 'O2000.NC')

        Returns:
            Upload result dict
        """
        def _upload_sync():
            ftp = None
            try:
                ftp = FTP()
                ftp.set_pasv(False)  # Use ACTIVE mode
                ftp.connect(self.ip_address, self.port, timeout=self.timeout)
                ftp.login(self.username, self.password)

                buffer = BytesIO(local_content)
                ftp.storbinary(f'STOR {remote_path}', buffer)
                ftp.quit()
                return True

            except Exception as e:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
                raise e

        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, _upload_sync),
                timeout=self.timeout
            )
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
        Delete file from CNC using active FTP mode.

        Args:
            remote_path: Path to file on CNC

        Returns:
            Deletion result dict
        """
        def _delete_sync():
            ftp = None
            try:
                ftp = FTP()
                ftp.set_pasv(False)  # Use ACTIVE mode
                ftp.connect(self.ip_address, self.port, timeout=self.timeout)
                ftp.login(self.username, self.password)

                ftp.delete(remote_path)
                ftp.quit()
                return True

            except Exception as e:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
                raise e

        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, _delete_sync),
                timeout=self.timeout
            )
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
