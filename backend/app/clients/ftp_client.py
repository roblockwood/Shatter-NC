"""FTP client for file operations with Brother CNC machines."""
import asyncio
from ftplib import FTP, error_perm
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
        timeout: int = 30,
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
        self.ftp: Optional[FTP] = None
        self._connected = False

    def _ensure_connection(self):
        """
        Establish or verify FTP connection.

        Creates a new connection if one doesn't exist or if the previous
        connection was lost. Uses passive mode for compatibility with
        Brother CNC machines.
        """
        if self.ftp is None or not self._connected:
            self.ftp = FTP()
            self.ftp.set_pasv(True)  # Use PASSIVE mode
            self.ftp.connect(self.ip_address, self.port, timeout=self.timeout)
            self.ftp.login(self.username, self.password)
            self._connected = True

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test FTP connection using passive mode.

        Tests both the ability to connect to the FTP server AND authenticate
        with the provided credentials.

        Returns:
            Dict with connection test results
        """
        def _test_sync():
            try:
                start_time = datetime.now()
                self._ensure_connection()
                # Get current directory to verify both connection and authentication
                current_dir = self.ftp.pwd()
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds() * 1000
                return latency, current_dir
            except Exception as e:
                self._connected = False
                raise e

        try:
            loop = asyncio.get_event_loop()
            latency, current_dir = await asyncio.wait_for(
                loop.run_in_executor(None, _test_sync),
                timeout=self.timeout
            )
            return {
                "success": True,
                "latency_ms": round(latency, 2),
                "current_directory": current_dir,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"FTP connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _parse_mlst_response(self, mlst_line: str) -> Dict[str, Any]:
        """Parse MLST response to extract file metadata."""
        parts = mlst_line.split(';')
        metadata = {}

        # Parse facts (everything except the last part which is the filename)
        for part in parts[:-1]:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                metadata[key.lower()] = value

        # Filename is the last part
        filename = parts[-1].strip() if parts else ''

        return {'filename': filename, 'metadata': metadata}

    def _parse_mlst_date(self, date_str: str) -> str:
        """Parse MLST date format (YYYYMMDDhhmmss) to ISO format."""
        try:
            if not date_str or len(date_str) != 14:
                return ""
            dt = datetime.strptime(date_str, "%Y%m%d%H%M%S")
            return dt.isoformat()
        except Exception as e:
            logger.debug(f"Error parsing date {date_str}: {e}")
            return ""

    async def list_files(self, path: str = "/") -> List[Dict[str, Any]]:
        """
        List files in CNC directory using passive FTP mode.

        Args:
            path: Directory path (default root)

        Returns:
            List of file information dicts
        """
        def _list_files_sync():
            """Synchronous FTP operations to run in thread pool."""
            try:
                self._ensure_connection()

                files = []
                # Use NLST for Brother CNC compatibility (MLSD can hang in passive mode)
                file_list = self.ftp.nlst(path) if path != "/" else self.ftp.nlst()

                # Remember current directory to restore later
                current_dir = self.ftp.pwd()

                for name in file_list:
                    is_directory = False
                    size = 0
                    modified = ""

                    # Try to get file size - fails for directories
                    try:
                        size = self.ftp.size(name)
                    except:
                        # SIZE failed, might be a directory - try to CWD into it
                        try:
                            self.ftp.cwd(name)
                            is_directory = True
                            # Restore to original directory
                            self.ftp.cwd(current_dir)
                        except:
                            # Not a directory, just a file where SIZE failed
                            pass

                    # Try to get modification date
                    try:
                        mlst_response = self.ftp.mlst(name)
                        if mlst_response:
                            parsed = self._parse_mlst_response(mlst_response)
                            if 'modify' in parsed['metadata']:
                                modified = self._parse_mlst_date(parsed['metadata']['modify'])
                    except:
                        # MLST not available, try alternative methods
                        try:
                            time_response = self.ftp.sendcmd('MDTM ' + name)
                            if time_response.startswith('213'):
                                date_str = time_response.split()[1]
                                modified = self._parse_mlst_date(date_str)
                        except:
                            # Can't get modification date
                            pass

                    files.append({
                        "name": name,
                        "path": f"/{name}",
                        "is_directory": is_directory,
                        "size": size,
                        "modified": modified,
                    })

                return files

            except Exception as e:
                self._connected = False
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
        Download file from CNC using passive FTP mode.

        Args:
            remote_path: Path to file on CNC (e.g., 'O2000.NC')

        Returns:
            File contents as bytes, or None on error
        """
        def _download_sync():
            try:
                self._ensure_connection()

                buffer = BytesIO()
                self.ftp.retrbinary(f'RETR {remote_path}', buffer.write)
                return buffer.getvalue()

            except Exception as e:
                self._connected = False
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
        Upload file to CNC using passive FTP mode.

        Args:
            local_content: File content as bytes
            remote_path: Destination path on CNC (e.g., 'O2000.NC')

        Returns:
            Upload result dict
        """
        def _upload_sync():
            try:
                self._ensure_connection()

                buffer = BytesIO(local_content)
                self.ftp.storbinary(f'STOR {remote_path}', buffer)
                return True

            except Exception as e:
                self._connected = False
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
        Delete file from CNC using passive FTP mode.

        Args:
            remote_path: Path to file on CNC

        Returns:
            Deletion result dict
        """
        def _delete_sync():
            try:
                self._ensure_connection()

                self.ftp.delete(remote_path)
                return True

            except Exception as e:
                self._connected = False
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

    async def get_programs(self, path: str = "/") -> List[Dict[str, Any]]:
        """
        Get list of all files and directories.

        Args:
            path: Directory path to list (default: /)

        Returns:
            List of all files with metadata (no filtering)
        """
        all_files = await self.list_files(path)
        return all_files

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

    async def connect(self) -> bool:
        """
        Explicitly establish FTP connection.

        Returns:
            True if connection successful
        """
        def _connect_sync():
            self._ensure_connection()
            return True

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _connect_sync)

    async def disconnect(self):
        """
        Explicitly close FTP connection.

        Closes the persistent FTP connection and cleans up resources.
        """
        def _disconnect_sync():
            if self.ftp and self._connected:
                try:
                    self.ftp.quit()
                except:
                    pass
                finally:
                    self._connected = False
                    self.ftp = None

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _disconnect_sync)

    def __del__(self):
        """
        Cleanup connection on object destruction.

        Ensures FTP connection is properly closed when the client
        object is garbage collected.
        """
        if self.ftp and self._connected:
            try:
                self.ftp.quit()
            except:
                pass


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
