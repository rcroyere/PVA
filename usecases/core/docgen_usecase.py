"""
DOCGEN use case - PDF generation from RabbitMQ messages
DAL connections:
  - RabbitMQ (Entrant, 5672, AMQP/TLS)
  - FileSystem (Sortant, 22, SFTP/SSH)
  - API-TO-PDF (Sortant, 8080, HTTPS)
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.rabbitmq_adapter import RabbitMQAdapter
from infrastructure.sftp_adapter import SFTPAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class DocgenUseCase(BaseServiceUseCase):
    """Test use case for DOCGEN - generates PDF documents from RabbitMQ to SFTP volume"""

    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="docgen",
            namespace="webapp-apis",
            env_config=env_config
        )
        self.rabbitmq_adapter = RabbitMQAdapter(self._k(env_config.get('rabbitmq', {})))
        self.sftp_adapter = SFTPAdapter(self._k(env_config.get('sftp', {})))

        ext = env_config.get('external_services', {})
        self.api_to_pdf_adapter = HTTPAdapter(self._k({'base_url': ext.get('api_to_pdf_url', 'http://api-to-pdf:8080')}))

    async def run_connectivity_tests(self) -> List[TestResult]:
        results = []

        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(self._create_test_result("rabbitmq_connectivity", TestCategory.CONNECTIVITY, Protocol.RABBITMQ, rabbitmq_result))

        rabbitmq_auth = await self.rabbitmq_adapter.test_authentication()
        results.append(self._create_test_result("rabbitmq_authentication", TestCategory.AUTHENTICATION, Protocol.RABBITMQ, rabbitmq_auth))

        sftp_result = await self.sftp_adapter.test_connectivity()
        results.append(self._create_test_result("sftp_connectivity", TestCategory.CONNECTIVITY, Protocol.SFTP, sftp_result))

        sftp_auth = await self.sftp_adapter.test_authentication()
        results.append(self._create_test_result("sftp_authentication", TestCategory.AUTHENTICATION, Protocol.SFTP, sftp_auth))

        api_pdf_result = await self.api_to_pdf_adapter.test_connectivity()
        results.append(self._create_test_result("api_to_pdf_connectivity", TestCategory.CONNECTIVITY, Protocol.HTTPS, api_pdf_result))

        return results

    async def run_functional_tests(self) -> List[TestResult]:
        results = []

        queue_result = await self.rabbitmq_adapter.test_queue_access("docgen.pdf.requests")
        results.append(self._create_test_result("rabbitmq_queue_pdf_requests", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, queue_result))

        test_message = {"service": "docgen", "test": "pdf_generation_check", "timestamp": time.time()}
        publish_result = await self.rabbitmq_adapter.test_publish_consume("docgen.pdf.requests", test_message)
        results.append(self._create_test_result("rabbitmq_publish_consume_e2e", TestCategory.FUNCTIONAL, Protocol.RABBITMQ, publish_result))

        sftp_ops = await self.sftp_adapter.test_file_operations()
        results.append(self._create_test_result("sftp_file_operations", TestCategory.FUNCTIONAL, Protocol.SFTP, sftp_ops))

        api_pdf_health = await self.api_to_pdf_adapter.test_health_check('/health')
        results.append(self._create_test_result("api_to_pdf_health_check", TestCategory.FUNCTIONAL, Protocol.HTTPS, api_pdf_health))

        return results

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rabbitmq_adapter.close()
        await self.sftp_adapter.close()
        await self.api_to_pdf_adapter.close()
