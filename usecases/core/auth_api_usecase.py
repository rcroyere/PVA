"""
AuthAPI use case - Middleware entre Front et API Customer Provider
DAL connections:
  - API REST (CoreAPI) (Sortant, 8080, HTTPS/mTLS)
  - Keycloak (Sortant, 8443, HTTPS/mTLS)
  - FileSystem (Sortant, 22, SFTP/SSH)
  - Memcached (Bidirectional)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.http_adapter import HTTPAdapter
from infrastructure.sftp_adapter import SFTPAdapter

logger = logging.getLogger(__name__)


class AuthAPIUseCase(BaseServiceUseCase):
    """Test use case for AuthAPI - authentication middleware"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="auth-api",
            namespace="webapp-apis",
            env_config=env_config
        )
        keycloak_config = env_config.get('keycloak', {})
        self.keycloak_adapter = HTTPAdapter(self._k({'base_url': keycloak_config.get('url', '')}))

        ext = env_config.get('external_services', {})
        self.core_api_adapter = HTTPAdapter(self._k({'base_url': ext.get('core_api_url', 'http://core-api:8080')}))

        self.sftp_adapter = SFTPAdapter(self._k(env_config.get('sftp', {})))

        service_config = env_config.get('services', {}).get('auth-api', {})
        service_url = f"http://{service_config.get('service_name', 'auth-api')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        core_api_result = await self.core_api_adapter.test_connectivity()
        results.append(self._create_test_result("core_api_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, core_api_result))

        keycloak_result = await self.keycloak_adapter.test_connectivity()
        results.append(self._create_test_result("keycloak_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, keycloak_result))

        keycloak_auth = await self.keycloak_adapter.test_authentication({'type': 'bearer', 'realm': self.env_config.get('keycloak', {}).get('realm', '')})
        results.append(self._create_test_result("keycloak_authentication", TestCategory.AUTHENTICATION, Protocol.HTTPS, keycloak_auth))

        sftp_result = await self.sftp_adapter.test_connectivity()
        results.append(self._create_test_result("sftp_connectivity", TestCategory.CONNECTIVITY, Protocol.SFTP, sftp_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        keycloak_health = await self.keycloak_adapter.test_health_check('/health')
        results.append(self._create_test_result("keycloak_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, keycloak_health))

        core_api_health = await self.core_api_adapter.test_health_check('/health')
        results.append(self._create_test_result("core_api_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, core_api_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.keycloak_adapter.close()
        await self.core_api_adapter.close()
        await self.sftp_adapter.close()
        await self.http_adapter.close()
