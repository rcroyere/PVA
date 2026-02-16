"""
observability-api use case
DAL connections:
  - Kafka (Sortant, 9092, SASL/TLS)

⚠️ Currently disabled due to performance issues and the need for major refactoring.
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol, TestStatus
from infrastructure.kafka_adapter import KafkaAdapter

logger = logging.getLogger(__name__)


class ObservabilityApiUseCase(BaseServiceUseCase):
    """
    Test use case for observability-api (CFK).
    ⚠️ Service is currently disabled - tests are skipped.
    """

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="observability-api",
            namespace="cfk-shared",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self._disabled = env_config.get('services', {}).get('observability-api', {}).get('disabled', True)

    def _skipped(self, test_name: str, protocol: Protocol) -> TestResult:
        return TestResult(
            test_name=test_name,
            service_name=self.service_name,
            category=TestCategory.CONNECTIVITY,
            protocol=protocol,
            status=TestStatus.SKIPPED,
            duration_ms=0,
            message="Service disabled - skipped"
        )

    async def run_connectivity_tests(self) -> List[TestResult]:
        if self._disabled:
            logger.warning("observability-api is disabled, skipping all tests")
            return [self._skipped("kafka_connectivity", Protocol.KAFKA)]

        results = []
        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        if self._disabled:
            return [self._skipped("kafka_topic_write", Protocol.KAFKA)]

        results = []
        env = self.env_config.get('environment', 'dev')
        topic = f"{env}.observability.flow.tracking"
        topic_result = await self.kafka_adapter.test_topic_access(topic, 'WRITE')
        results.append(self._create_test_result(f"kafka_topic_write_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
