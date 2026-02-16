"""
KMS API use case - Key Management Service
DAL connections:
  - GCP KMS (Sortant, 443, HTTPS/mTLS)
  - PostgreSQL KMS (Bidirectional)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class KmsApiUseCase(BaseServiceUseCase):
    """Test use case for KMS API - key management service backed by Google Cloud KMS"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="kms-api",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('kms', {})))

        ext = env_config.get('external_services', {})
        self.gcp_kms_adapter = HTTPAdapter(self._k({'base_url': ext.get('gcp_kms_url', 'https://cloudkms.googleapis.com')}))

        service_config = env_config.get('services', {}).get('kms-api', {})
        service_url = f"http://{service_config.get('service_name', 'kms-api')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_kms_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_kms_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        gcp_result = await self.gcp_kms_adapter.test_connectivity()
        results.append(self._create_test_result("gcp_kms_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, gcp_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        api_health = await self.http_adapter.test_health_check('/api/health')
        results.append(self._create_test_result("api_health_check", TestCategory.FUNCTIONAL, Protocol.HTTP, api_health))

        keys_endpoint = await self.http_adapter.test_endpoint('/api/v1/keys', 'GET')
        results.append(self._create_test_result("keys_endpoint_accessible", TestCategory.FUNCTIONAL, Protocol.HTTP, keys_endpoint))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pg_adapter.close()
        await self.gcp_kms_adapter.close()
        await self.http_adapter.close()
