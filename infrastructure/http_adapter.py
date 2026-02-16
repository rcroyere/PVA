"""
HTTP adapter for REST API connectivity and functional testing
"""
import time
import asyncio
import requests
from typing import Dict, Any, Optional
import logging

from .base_adapter import BaseAdapter, ConnectionResult

logger = logging.getLogger(__name__)


class HTTPAdapter(BaseAdapter):
    """HTTP/HTTPS REST API connectivity adapter"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url')
        self.verify_ssl = config.get('verify_ssl', True)
        self.session = requests.Session()

        # Set default headers
        if 'headers' in config:
            self.session.headers.update(config['headers'])

        # kubectl mode: test from within the pod via kubectl exec (curl)
        self._kubectl = config.get('_kubectl')
    
    async def test_connectivity(self) -> ConnectionResult:
        """Test HTTP endpoint connectivity"""
        if self._kubectl:
            return await self._kubectl['executor'].test_http(
                self._kubectl['namespace'], self._kubectl['pod'],
                self.base_url
            )

        start_time = time.time()

        try:
            # Try a HEAD request first (lightweight)
            response = self.session.head(
                self.base_url,
                verify=self.verify_ssl,
                timeout=self.connection_config.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code < 500:  # Accept any non-server-error
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Successfully connected to {self.base_url}",
                    metadata={
                        'url': self.base_url,
                        'status_code': response.status_code,
                        'headers': dict(response.headers)
                    }
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Server error: HTTP {response.status_code}"
                )
                
        except requests.exceptions.ConnectionError as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Connection failed: {str(e)}"
            )
            
        except requests.exceptions.Timeout as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Connection timeout after {self.connection_config.timeout}s"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"HTTP connectivity test failed: {str(e)}"
            )
    
    async def test_authentication(self, auth_config: Optional[Dict[str, Any]] = None) -> ConnectionResult:
        """Test HTTP authentication"""
        if self._kubectl:
            result = await self.test_connectivity()
            result.metadata['note'] = 'token-based authentication not testable in kubectl mode'
            return result

        start_time = time.time()

        try:
            # Setup authentication
            if auth_config:
                if 'bearer_token' in auth_config:
                    self.session.headers.update({
                        'Authorization': f"Bearer {auth_config['bearer_token']}"
                    })
                elif 'basic_auth' in auth_config:
                    from requests.auth import HTTPBasicAuth
                    username = auth_config['basic_auth']['username']
                    password = auth_config['basic_auth']['password']
                    auth = HTTPBasicAuth(username, password)
                    self.session.auth = auth
            
            # Test with an authenticated endpoint
            auth_endpoint = auth_config.get('test_endpoint', self.base_url)
            
            response = self.session.get(
                auth_endpoint,
                verify=self.verify_ssl,
                timeout=self.connection_config.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message="HTTP authentication successful",
                    metadata={
                        'status_code': response.status_code,
                        'endpoint': auth_endpoint
                    }
                )
            elif response.status_code == 401:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error="Authentication failed: Invalid credentials (401)"
                )
            elif response.status_code == 403:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error="Authentication failed: Access forbidden (403)"
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Unexpected status code: {response.status_code}"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"HTTP authentication test failed: {str(e)}"
            )
    
    async def test_endpoint(
        self, 
        endpoint: str, 
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None,
        expected_status: int = 200
    ) -> ConnectionResult:
        """Test a specific HTTP endpoint"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=data if data else None,
                verify=self.verify_ssl,
                timeout=self.connection_config.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            success = response.status_code == expected_status
            
            result = ConnectionResult(
                success=success,
                duration_ms=duration_ms,
                message=f"{method} {endpoint} returned {response.status_code}" if success else None,
                error=None if success else f"Expected {expected_status}, got {response.status_code}",
                metadata={
                    'method': method,
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response_size': len(response.content),
                    'content_type': response.headers.get('Content-Type')
                }
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Endpoint test failed for {method} {endpoint}: {str(e)}"
            )
    
    async def test_health_check(self, health_endpoint: str = '/health') -> ConnectionResult:
        """Test service health endpoint"""
        url = f"{self.base_url.rstrip('/')}/{health_endpoint.lstrip('/')}"

        if self._kubectl:
            return await self._kubectl['executor'].test_http(
                self._kubectl['namespace'], self._kubectl['pod'], url
            )

        start_time = time.time()

        try:
            
            response = self.session.get(
                url,
                verify=self.verify_ssl,
                timeout=self.connection_config.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            is_healthy = response.status_code == 200
            
            health_data = {}
            try:
                health_data = response.json()
            except:
                pass
            
            return ConnectionResult(
                success=is_healthy,
                duration_ms=duration_ms,
                message="Service is healthy" if is_healthy else f"Service unhealthy: {response.status_code}",
                metadata={
                    'health_endpoint': health_endpoint,
                    'status_code': response.status_code,
                    'health_data': health_data
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Health check failed: {str(e)}"
            )
    
    async def close(self):
        """Close HTTP session"""
        try:
            self.session.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP session: {e}")
