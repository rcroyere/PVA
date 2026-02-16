"""
PSO IO Webhook use case
DAL connections:
  - RabbitMQ (Entrant, 5672, AMQP/TLS)
  - PostgreSQL CoreDB (Bidirectional, 5432, mTLS)
  - Memcached (Bidirectional)
  - Keycloak (Sortant, 8443, HTTPS/mTLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.rabbitmq_adapter import RabbitMQAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class PSOIoWebhookUseCase(BaseServiceUseCase):
    """Test use case for PSO IO Webhook - publishes PSO creation events"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="pso-io-webhook",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.rabbitmq_adapter = RabbitMQAdapter(self._k(env_config.get('rabbitmq', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('core_db', {})))

        keycloak_config = env_config.get('keycloak', {})
        self.keycloak_adapter = HTTPAdapter(self._k({'base_url': keycloak_config.get('url', '')}))

        service_config = env_config.get('services', {}).get('pso-io-webhook', {})
        service_url = f"http://{service_config.get('service_name', 'pso-io-webhook')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(self._create_test_result("rabbitmq_connectivity", TestCategory.CONNECTIVITY, Protocol.RABBITMQ, rabbitmq_result))

        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
        results.append(self._create_test_result("rabbitmq_authentication", TestCategory.AUTHENTICATION, Protocol.RABBITMQ, rabbitmq_auth))

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_coredb_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_coredb_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        keycloak_result = await self.keycloak_adapter.test_connectivity()
        results.append(self._create_test_result("keycloak_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, keycloak_result))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        queue_result = await self.rabbitmq_adapter.test_queue_access("pso.io.webhook.events")
        results.append(self._create_test_result("rabbitmq_queue_webhook_events", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, queue_result))

        test_message = {"service": "pso-io-webhook", "test": "pso_creation_check", "timestamp": time.time()}
        publish_result = await self.rabbitmq_adapter.test_publish_consume("pso.io.webhook.events", test_message)
        results.append(self._create_test_result("rabbitmq_publish_consume_e2e", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, publish_result))

        keycloak_health = await self.keycloak_adapter.test_health_check('/health')
        results.append(self._create_test_result("keycloak_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, keycloak_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rabbitmq_adapter.close()
        await self.pg_adapter.close()
        await self.keycloak_adapter.close()
        await self.http_adapter.close()
