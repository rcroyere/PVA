"""
Search Engine API use case - HTTP API + RabbitMQ consumer for ElasticSearch
DAL connections:
  - PostgreSQL Search Engine (Bidirectional, 5432, mTLS)
  - API REST CoreAPI (Bidirectional, 8003, mTLS)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class SearchEngineApiUseCase(BaseServiceUseCase):
    """Test use case for Search Engine API - HTTP endpoint for search with ElasticSearch"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="search-engine-api",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('search_engine', {})))

        ext = env_config.get('external_services', {})
        self.core_api_adapter = HTTPAdapter(self._k({'base_url': ext.get('core_api_url', 'http://core-api:8080')}))

        service_config = env_config.get('services', {}).get('search-engine-api', {})
        service_url = f"http://{service_config.get('service_name', 'search-engine-api')}:{service_config.get('port', 9200)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_search_engine_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_search_engine_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        core_api_result = await self.core_api_adapter.test_connectivity()
        results.append(self._create_test_result("core_api_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, core_api_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        search_health = await self.http_adapter.test_health_check('/health')
        results.append(self._create_test_result("search_api_health", TestCategory.FUNCTIONAL, Protocol.HTTP, search_health))

        search_endpoint = await self.http_adapter.test_endpoint('/api/v1/search', 'GET')
        results.append(self._create_test_result("search_endpoint_accessible", TestCategory.FUNCTIONAL, Protocol.HTTP, search_endpoint))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pg_adapter.close()
        await self.core_api_adapter.close()
        await self.http_adapter.close()
