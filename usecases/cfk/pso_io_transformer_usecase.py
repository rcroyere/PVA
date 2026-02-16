"""
pso-io-transformer use case
DAL connections:
  - Kafka (Bidirectional, 9092, SASL/TLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class PSOIoTransformerUseCase(BaseServiceUseCase):
    """Test use case for pso-io-transformer (CFK) - applies transformation rules to client data"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="pso-io-transformer",
            namespace="cfk-shared",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))

        service_config = env_config.get('services', {}).get('pso-io-transformer', {})
        service_url = f"http://{service_config.get('service_name', 'pso-io-transformer')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        env = self.env_config.get('environment', 'dev')
        for topic, access in [
            (f"{env}.io.transformer.rules.input", 'READ'),
            (f"{env}.io.transformer.rules.output", 'WRITE'),
        ]:
            topic_result = await self.kafka_adapter.test_topic_access(topic, access)
            results.append(self._create_test_result(
                f"kafka_topic_{access.lower()}_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result
            ))

        test_message = {"service": "pso-io-transformer", "test": "connectivity_check"}
        produce_result = await self.kafka_adapter.test_produce_consume(f"{env}.io.transformer.rules.output", test_message)
        results.append(self._create_test_result("kafka_produce_consume_e2e", TestCategory.FUNCTIONAL, Protocol.KAFKA, produce_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.http_adapter.close()
