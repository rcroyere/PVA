"""
temporal-translator use case
DAL connections:
  - Kafka (Bidirectional, 8080, mTLS/HTTPS)
  - Temporal.io (Sortant, 8080, mTLS/HTTPS)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class TemporalTranslatorUseCase(BaseServiceUseCase):
    """Test use case for temporal-translator (CFK) - prepares Temporal.io workflow payloads"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="temporal-translator",
            namespace="cfk-out",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))

        temporal_url = env_config.get('external_services', {}).get('temporal_url', '')
        self.temporal_adapter = HTTPAdapter(self._k({'base_url': temporal_url}))

        service_config = env_config.get('services', {}).get('temporal-translator', {})
        service_url = f"http://{service_config.get('service_name', 'temporal-translator')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        temporal_result = await self.temporal_adapter.test_connectivity()
        results.append(self._create_test_result("temporal_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, temporal_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        env = self.env_config.get('environment', 'dev')
        for topic, access in [
            (f"{env}.temporal.translator.input", 'READ'),
            (f"{env}.temporal.translator.workflows", 'WRITE'),
        ]:
            topic_result = await self.kafka_adapter.test_topic_access(topic, access)
            results.append(self._create_test_result(
                f"kafka_topic_{access.lower()}_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result
            ))

        temporal_ns = await self.temporal_adapter.test_health_check('/api/v1/namespaces')
        results.append(self._create_test_result("temporal_namespaces_access", TestCategory.FUNCTIONAL, Protocol.HTTPS, temporal_ns))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.temporal_adapter.close()
        await self.http_adapter.close()
