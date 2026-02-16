"""
Search Engine Consumer use case - RabbitMQ consumer to update search index
DAL connections:
  - RabbitMQ (Entrant, 5672, AMQP/TLS)
  - PostgreSQL Search Engine (Sortant, 5432, mTLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.rabbitmq_adapter import RabbitMQAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter

logger = logging.getLogger(__name__)


class SearchEngineConsumerUseCase(BaseServiceUseCase):
    """Test use case for Search Engine Consumer - consumes indexation events from RabbitMQ"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="search-engine-consumer",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.rabbitmq_adapter = RabbitMQAdapter(self._k(env_config.get('rabbitmq', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('search_engine', {})))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(self._create_test_result("rabbitmq_connectivity", TestCategory.CONNECTIVITY, Protocol.RABBITMQ, rabbitmq_result))

        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
        results.append(self._create_test_result("rabbitmq_authentication", TestCategory.AUTHENTICATION, Protocol.RABBITMQ, rabbitmq_auth))

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_search_engine_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_search_engine_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        queue_result = await self.rabbitmq_adapter.test_queue_access("search.indexation.events")
        results.append(self._create_test_result("rabbitmq_queue_indexation_events", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, queue_result))

        test_message = {"service": "search-engine-consumer", "test": "indexation_check", "timestamp": time.time()}
        publish_result = await self.rabbitmq_adapter.test_publish_consume("search.indexation.events", test_message)
        results.append(self._create_test_result("rabbitmq_publish_consume_e2e", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, publish_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rabbitmq_adapter.close()
        await self.pg_adapter.close()
