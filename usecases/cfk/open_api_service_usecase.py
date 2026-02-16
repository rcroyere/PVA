"""
open-api-service use case
DAL connections:
  - PostgreSQL CFK (openapi/openapi, 5432, TLS)
  - Kafka (Sortant, 9092, SASL/TLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class OpenApiServiceUseCase(BaseServiceUseCase):
    """Test use case for open-api-service (CFK)"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="open-api-service",
            namespace="cfk-shared",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('cfk_openapi', {})))

        service_config = env_config.get('services', {}).get('open-api-service', {})
        service_url = f"http://{service_config.get('service_name', 'open-api-service')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_cfk_openapi_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_cfk_openapi_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        env = self.env_config.get('environment', 'dev')
        topic = f"{env}.openapi.webhook.events"
        topic_result = await self.kafka_adapter.test_topic_access(topic, 'WRITE')
        results.append(self._create_test_result(f"kafka_topic_write_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
        await self.http_adapter.close()
