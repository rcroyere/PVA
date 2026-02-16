"""
BackOffice use case - exposed via VPN in preprod/prod
DAL connections:
  - AuthAPI (Sortant, 8080, HTTPS/mTLS + VPN)
  - PostgreSQL Gateway (Bidirectional, 5432, mTLS + VPN)
  - PostgreSQL Search Engine (Bidirectional, 5432, mTLS)
  - Keycloak DB (Bidirectional, 5432, mTLS) - direct DB access (avoid - prefer API)
  - Kafka (Bidirectional, 9092, SASL/TLS)
  - Github (Bidirectional, 80, SASL/TLS) - Ansible Workflow
  - Visier (Bidirectional, 80, SASL/TLS) - API Visier
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class BackofficeUseCase(BaseServiceUseCase):
    """Test use case for BackOffice (CoreAPI) - admin interface exposed via VPN"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="backoffice",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_gateway_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('gateway', {})))
        self.pg_search_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('search_engine', {})))

        ext = env_config.get('external_services', {})
        self.auth_api_adapter = HTTPAdapter(self._k({'base_url': ext.get('auth_api_url', 'http://auth-api:8080')}))

        service_config = env_config.get('services', {}).get('backoffice', {})
        service_url = f"http://{service_config.get('service_name', 'backoffice')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        pg_gateway_result = await self.pg_gateway_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_gateway_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_gateway_result))

        pg_search_result = await self.pg_search_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_search_engine_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_search_result))

        auth_api_result = await self.auth_api_adapter.test_connectivity()
        results.append(self._create_test_result("auth_api_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, auth_api_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        env = self.env_config.get('environment', 'dev')
        topic = f"{env}.backoffice.in.request.data.json"
        topic_result = await self.kafka_adapter.test_topic_access(topic, 'READ')
        results.append(self._create_test_result(f"kafka_topic_read_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result))

        auth_health = await self.auth_api_adapter.test_health_check('/health')
        results.append(self._create_test_result("auth_api_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, auth_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.pg_gateway_adapter.close()
        await self.pg_search_adapter.close()
        await self.auth_api_adapter.close()
        await self.http_adapter.close()
