"""
archive-service use case
DAL connections:
  - PostgreSQL CFK (archive/archive, 5432, TLS)
  - Kafka (Bidirectional, 22, SSH/SFTP)
  - GCP Secret Manager (Bidirectional, 8080, mTLS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.sftp_adapter import SFTPAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class ArchiveServiceUseCase(BaseServiceUseCase):
    """Test use case for archive-service (CFK)"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="archive-service",
            namespace="cfk-shared",
            env_config=env_config
        )
        self.kafka_adapter = KafkaAdapter(self._k(env_config.get('kafka', {})))
        self.pg_adapter = PostgreSQLAdapter(self._k(env_config.get('postgresql', {}).get('cfk_archive', {})))
        self.sftp_adapter = SFTPAdapter(self._k(env_config.get('sftp', {})))
        gcp_url = env_config.get('external_services', {}).get('gcp_secret_manager_url', '')
        self.gcp_adapter = HTTPAdapter(self._k({'base_url': gcp_url}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(self._create_test_result("kafka_connectivity", TestCategory.CONNECTIVITY, Protocol.KAFKA, kafka_result))

        kafka_auth = await self.kafka_adapter.test_authentication()
        results.append(self._create_test_result("kafka_authentication", TestCategory.AUTHENTICATION, Protocol.KAFKA, kafka_auth))

        pg_result = await self.pg_adapter.test_connectivity()
        results.append(self._create_test_result("postgresql_cfk_archive_connectivity", TestCategory.CONNECTIVITY, Protocol.POSTGRESQL, pg_result))

        pg_auth = await self.pg_adapter.test_authentication()
        results.append(self._create_test_result("postgresql_cfk_archive_authentication", TestCategory.AUTHENTICATION, Protocol.POSTGRESQL, pg_auth))

        sftp_result = await self.sftp_adapter.test_connectivity()
        results.append(self._create_test_result("sftp_connectivity", TestCategory.CONNECTIVITY, Protocol.SFTP, sftp_result))

        sftp_auth = await self.sftp_adapter.test_authentication()
        results.append(self._create_test_result("sftp_authentication", TestCategory.AUTHENTICATION, Protocol.SFTP, sftp_auth))

        gcp_result = await self.gcp_adapter.test_connectivity()
        results.append(self._create_test_result("gcp_secret_manager_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, gcp_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        sftp_ops = await self.sftp_adapter.test_file_operations()
        results.append(self._create_test_result("sftp_file_operations", TestCategory.FUNCTIONAL, Protocol.SFTP, sftp_ops))

        env = self.env_config.get('environment', 'dev')
        topic = f"{env}.archive.executions"
        topic_result = await self.kafka_adapter.test_topic_access(topic, 'READ')
        results.append(self._create_test_result(f"kafka_topic_read_{topic}", TestCategory.FUNCTIONAL, Protocol.KAFKA, topic_result))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
        await self.sftp_adapter.close()
        await self.gcp_adapter.close()
