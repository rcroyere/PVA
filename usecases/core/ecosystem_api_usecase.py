"""
Ecosystem-API use case
DAL connections:
  - PostgreSQL EcosystemDB (Bidirectional, 5432, mTLS)
  - Keycloak (Sortant, 8443, HTTPS/mTLS)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class EcosystemApiUseCase(BaseServiceUseCase):
    """Test use case for Ecosystem-API"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="ecosystem-api",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('ecosystem', {})))

        keycloak_config = env_config.get('keycloak', {})
        self.keycloak_adapter = HTTPAdapter(self._k({'base_url': keycloak_config.get('url', '')}))

        service_config = env_config.get('services', {}).get('ecosystem-api', {})
        service_url = f"http://{service_config.get('service_name', 'ecosystem-api')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_ecosystem_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_ecosystem_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        keycloak_result = await self.keycloak_adapter.test_connectivity()
        results.append(self._create_test_result("keycloak_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, keycloak_result))

        keycloak_auth = await self.keycloak_adapter.test_authentication({'type': 'bearer', 'realm': self.env_config.get('keycloak', {}).get('realm', '')})
        results.append(self._create_test_result("keycloak_authentication", TestCategory.AUTHENTICATION, Protocol.HTTPS, keycloak_auth))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        keycloak_health = await self.keycloak_adapter.test_health_check('/health')
        results.append(self._create_test_result("keycloak_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, keycloak_health))

        api_health = await self.http_adapter.test_health_check('/api/health')
        results.append(self._create_test_result("api_health_check", TestCategory.FUNCTIONAL, Protocol.HTTP, api_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pg_adapter.close()
        await self.keycloak_adapter.close()
        await self.http_adapter.close()
