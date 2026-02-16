"""
RabbitConsumer (CoreAPI) use case
DAL connections:
  - RabbitMQ (Bidirectional, 5672, AMQP/TLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.rabbitmq_adapter import RabbitMQAdapter

logger = logging.getLogger(__name__)


class RabbitConsumerUseCase(BaseServiceUseCase):
    """Test use case for RabbitConsumer (CoreAPI) - processes RabbitMQ messages"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="rabbit-consumer",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.rabbitmq_adapter = RabbitMQAdapter(self._k(env_config.get('rabbitmq', {})))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(self._create_test_result("rabbitmq_connectivity", TestCategory.CONNECTIVITY, Protocol.RABBITMQ, rabbitmq_result))

        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
        results.append(self._create_test_result("rabbitmq_authentication", TestCategory.AUTHENTICATION, Protocol.RABBITMQ, rabbitmq_auth))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        queue_result = await self.rabbitmq_adapter.test_queue_access("core.consumer.queue")
        results.append(self._create_test_result("rabbitmq_queue_consumer", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, queue_result))

        test_message = {"service": "rabbit-consumer", "test": "connectivity_check", "timestamp": time.time()}
        publish_result = await self.rabbitmq_adapter.test_publish_consume("core.consumer.queue", test_message)
        results.append(self._create_test_result("rabbitmq_publish_consume_e2e", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, publish_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rabbitmq_adapter.close()
