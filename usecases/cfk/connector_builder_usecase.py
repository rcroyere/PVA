"""
connector-builder (BFF) use case
DAL connections:
  - Temporal.io (Bidirectional, 8080, mTLS)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class ConnectorBuilderUseCase(BaseServiceUseCase):
    """Test use case for connector-builder BFF (CFK)"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="connector-builder",
            namespace="cfk-shared",
            env_config=env_config
        )
        temporal_url = env_config.get('external_services', {}).get('temporal_url', '')
        self.temporal_adapter = HTTPAdapter(self._k({'base_url': temporal_url}))

        service_config = env_config.get('services', {}).get('connector-builder', {})
        service_url = f"http://{service_config.get('service_name', 'connector-builder')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        temporal_result = await self.temporal_adapter.test_connectivity()
        results.append(self._create_test_result("temporal_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, temporal_result))

        http_result = await self.http_adapter.test_connectivity()
        results.append(self._create_test_result("http_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTP, http_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        temporal_health = await self.temporal_adapter.test_health_check('/api/v1/namespaces')
        results.append(self._create_test_result("temporal_namespaces_access", TestCategory.FUNCTIONAL, Protocol.HTTPS, temporal_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.temporal_adapter.close()
        await self.http_adapter.close()
