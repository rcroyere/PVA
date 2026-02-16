"""
Queue Worker (CoreAPI) use case
DAL connections:
  - RabbitMQ (Sortant, 5672, AMQP/TLS)
  - PostgreSQL CoreDB (Bidirectional, 5432, mTLS)
  - PostgreSQL Gateway Talend (Bidirectional, 5432, mTLS)
  - Search Engine API (Sortant, 9200, HTTPS/mTLS)
  - KMS API (Sortant, 8080, HTTPS/mTLS)
  - Keycloak (Sortant, 8443, HTTPS/mTLS)
  - FileSystem (Sortant, 22, SFTP/SSH)
  - Memcached (Bidirectional)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.rabbitmq_adapter import RabbitMQAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter
from infrastructure.sftp_adapter import SFTPAdapter

logger = logging.getLogger(__name__)


class QueueWorkerUseCase(BaseServiceUseCase):
    """Test use case for Queue Worker (CoreAPI) - 1 process per customer"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="queue-worker",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.rabbitmq_adapter = RabbitMQAdapter(self._k(env_config.get('rabbitmq', {})))
        self.pg_core_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('core_db', {})))
        self.pg_gateway_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('gateway', {})))
        self.sftp_adapter = SFTPAdapter(self._k(env_config.get('sftp', {})))

        keycloak_config = env_config.get('keycloak', {})
        self.keycloak_adapter = HTTPAdapter(self._k({'base_url': keycloak_config.get('url', '')}))

        ext = env_config.get('external_services', {})
        self.kms_adapter = HTTPAdapter(self._k({'base_url': ext.get('kms_api_url', 'http://kms-api:8080')}))
        self.search_adapter = HTTPAdapter(self._k({'base_url': ext.get('search_engine_api_url', 'http://search-engine-api:9200')}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(self._create_test_result("rabbitmq_connectivity", TestCategory.CONNECTIVITY, Protocol.RABBITMQ, rabbitmq_result))

        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
        results.append(self._create_test_result("rabbitmq_authentication", TestCategory.AUTHENTICATION, Protocol.RABBITMQ, rabbitmq_auth))

        pg_core_result = await self.pg_core_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_coredb_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_core_result))

        pg_gateway_result = await self.pg_gateway_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_gateway_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_gateway_result))

        sftp_result = await self.sftp_adapter.test_connectivity()
        results.append(self._create_test_result("sftp_connectivity", TestCategory.CONNECTIVITY, Protocol.SFTP, sftp_result))

        keycloak_result = await self.keycloak_adapter.test_connectivity()
        results.append(self._create_test_result("keycloak_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, keycloak_result))

        kms_result = await self.kms_adapter.test_connectivity()
        results.append(self._create_test_result("kms_api_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTP, kms_result))

        search_result = await self.search_adapter.test_connectivity()
        results.append(self._create_test_result("search_engine_connectivity", TestCategory.CONNECTIVITY, Protocol.ELASTICSEARCH, search_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        queue_result = await self.rabbitmq_adapter.test_queue_access("core.worker.jobs")
        results.append(self._create_test_result("rabbitmq_queue_worker_jobs", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, queue_result))

        test_message = {"service": "queue-worker", "test": "connectivity_check", "timestamp": time.time()}
        publish_result = await self.rabbitmq_adapter.test_publish_consume("core.worker.jobs", test_message)
        results.append(self._create_test_result("rabbitmq_publish_consume_e2e", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, publish_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rabbitmq_adapter.close()
        await self.pg_core_adapter.close()
        await self.pg_gateway_adapter.close()
        await self.sftp_adapter.close()
        await self.keycloak_adapter.close()
        await self.kms_adapter.close()
        await self.search_adapter.close()
