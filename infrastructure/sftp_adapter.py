"""
SFTP adapter for file transfer connectivity testing
"""
import time
import asyncio
import paramiko
from typing import Dict, Any, Optional
import logging
import io

from .base_adapter import BaseAdapter, ConnectionResult

logger = logging.getLogger(__name__)


class SFTPAdapter(BaseAdapter):
    """SFTP connectivity adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
    
    async def test_connectivity(self) -> ConnectionResult:
        """Test SFTP server connectivity"""
        start_time = time.time()
        
        try:
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to SFTP server
            self.client.connect(
                hostname=self.config.get('host'),
                port=self.config.get('port', 22),
                username=self.config.get('username'),
                password=self.config.get('password'),
                timeout=self.connection_config.timeout
            )
            
            # Open SFTP session
            self.sftp = self.client.open_sftp()
            
            # Get server version
            server_version = self.sftp.get_channel().transport.remote_version
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Successfully connected to SFTP server {self.config.get('host')}",
                metadata={
                    'host': self.config.get('host'),
                    'port': self.config.get('port', 22),
                    'server_version': server_version
                }
            )
            
        except paramiko.AuthenticationException as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"SFTP authentication failed: {str(e)}"
            )
            
        except paramiko.SSHException as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"SFTP connection failed: {str(e)}"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"SFTP connectivity test failed: {str(e)}"
            )
    
    async def test_authentication(self) -> ConnectionResult:
        """Test SFTP authentication"""
        start_time = time.time()
        
        try:
            # Create new client for auth test
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try to connect
            client.connect(
                hostname=self.config.get('host'),
                port=self.config.get('port', 22),
                username=self.config.get('username'),
                password=self.config.get('password'),
                timeout=self.connection_config.timeout
            )
            
            # Open SFTP to verify full access
            sftp = client.open_sftp()
            
            # Try to list directory
            sftp.listdir('.')
            
            sftp.close()
            client.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message="SFTP authentication successful",
                metadata={
                    'username': self.config.get('username'),
                    'host': self.config.get('host')
                }
            )
            
        except paramiko.AuthenticationException as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"SFTP authentication failed: Invalid credentials"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"SFTP authentication test failed: {str(e)}"
            )
    
    async def test_directory_access(self, directory_path: str) -> ConnectionResult:
        """Test access to a specific directory"""
        start_time = time.time()
        
        try:
            if not self.sftp:
                await self.test_connectivity()
            
            # Try to list directory
            files = self.sftp.listdir(directory_path)
            
            # Get directory stats
            stat = self.sftp.stat(directory_path)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Directory '{directory_path}' is accessible",
                metadata={
                    'directory': directory_path,
                    'file_count': len(files),
                    'permissions': oct(stat.st_mode)
                }
            )
            
        except FileNotFoundError:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Directory '{directory_path}' does not exist"
            )
            
        except PermissionError:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Permission denied for directory '{directory_path}'"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Directory access test failed: {str(e)}"
            )
    
    async def test_file_upload_download(self, test_directory: str = '/tmp') -> ConnectionResult:
        """Test file upload and download operations"""
        start_time = time.time()
        
        try:
            if not self.sftp:
                await self.test_connectivity()
            
            # Create test file content
            test_content = f"Test file created at {time.time()}"
            test_filename = f"test_{int(time.time() * 1000)}.txt"
            test_path = f"{test_directory.rstrip('/')}/{test_filename}"
            
            # Upload test file
            file_obj = io.BytesIO(test_content.encode('utf-8'))
            self.sftp.putfo(file_obj, test_path)
            
            # Download test file
            downloaded = io.BytesIO()
            self.sftp.getfo(test_path, downloaded)
            
            # Verify content
            downloaded.seek(0)
            downloaded_content = downloaded.read().decode('utf-8')
            
            upload_success = downloaded_content == test_content
            
            # Cleanup
            try:
                self.sftp.remove(test_path)
            except:
                pass
            
            duration_ms = (time.time() - start_time) * 1000
            
            if upload_success:
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Successfully uploaded and downloaded file to {test_directory}",
                    metadata={
                        'test_file': test_filename,
                        'directory': test_directory,
                        'file_size': len(test_content)
                    }
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error="File content mismatch after upload/download"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"File upload/download test failed: {str(e)}"
            )
    
    async def close(self):
        """Close SFTP connection"""
        try:
            if self.sftp:
                self.sftp.close()
            if self.client:
                self.client.close()
        except Exception as e:
            logger.warning(f"Error closing SFTP connection: {e}")
