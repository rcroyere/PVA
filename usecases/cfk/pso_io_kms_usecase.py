"""
pso-io-kms use case
DAL connections:
  - PostgreSQL CFK (kms/pso_io_kms, 5432, TLS)
  - Kafka (Event/Async, SASL/TLS)
"""
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class PSOIoKmsUseCase(BaseServiceUseCase):
    """Test use case for pso-io-kms (CFK) - ID mapping store between PeopleSpheres and partner systems"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="pso-io-kms",
            namespace="cfk-shared",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('cfk_kms', {})))

        service_config = env_config.get('services', {}).get('pso-io-kms', {})
        service_url = f"http://{service_config.get('service_name', 'pso-io-kms')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter(self._k({'base_url': service_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_cfk_kms_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_cfk_kms_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        health_result = await self.http_adapter.test_health_check()
        results.append(self._create_test_result("health_check", TestCategory.CONNECTIVITY, Protocol.HTTP, health_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        env = self.env_config.get('environment', 'dev')
        for topic, access in [
            (f"{env}.io.kms.id.mappings", 'READ'),
            (f"{env}.io.kms.id.mappings.events", 'WRITE'),
        ]:
            topic_result = await self.kafka_adapter.test_topic_access(topic, access)
            results.append(self._create_test_result(
                f"kafka_topic_{access.lower()}_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result
            ))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
        await self.http_adapter.close()
