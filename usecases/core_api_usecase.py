"""
Core API service test use case
Based on flux matrix - Core Services
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


class CoreAPIUseCase(BaseServiceUseCase):
    """
    Test use case for API REST (CoreAPI) service
    
    Expected flows from matrix:
    - Search Engine API (HTTP + ElasticSearch, Bidirectional, 9200, HTTPS/mTLS)
    - KMS API (Sortant, 8080, HTTPS/mTLS)
    - RabbitMQ (Sortant, 5672, AMQP/TLS)
    - PostgreSQL CoreDB (Bidirectional, 5432, mTLS)
    - PostgreSQL Gateway Talend (Bidirectional, 5432, mTLS)
    - Keycloak (Sortant, 8443, HTTPS/mTLS)
    - FileSystem (Sortant, 22, SFTP/SSH)
    - Memcached (Bidirectionnel)
    - Bugsnag (Bidirectionnel)
    """
    
    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="API REST CoreAPI",
            namespace="webapp-apis",
            env_config=env_config
        )
        
        # Initialize adapters
        self.rabbitmq_adapter = RabbitMQAdapter(env_config.get('rabbitmq', {}))
        self.pg_core_adapter = PostgreSQLAdapter(env_config.get('postgresql', {}).get('core_db', {}))
        self.pg_gateway_adapter = PostgreSQLAdapter(env_config.get('postgresql', {}).get('gateway', {}))
        
        # HTTP adapters for various services
        keycloak_config = env_config.get('keycloak', {})
        self.keycloak_adapter = HTTPAdapter({'base_url': keycloak_config.get('url', '')})
        
        kms_url = "http://kms-api:8080"
        self.kms_adapter = HTTPAdapter({'base_url': kms_url})
        
        search_engine_url = "http://search-engine-api:9200"
        self.search_adapter = HTTPAdapter({'base_url': search_engine_url})
    
    async def run_connectivity_tests(self) -> List[TestResult]:
        """Run connectivity tests"""
        results = []
        
        # Test 1: RabbitMQ connectivity
        logger.info(f"Testing RabbitMQ connectivity for {self.service_name}")
        rabbitmq_result = await self.rabbitmq_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="rabbitmq_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.RABBITMQ,
                connection_result=rabbitmq_result
            )
        )
        
        # Test 2: RabbitMQ authentication
        rabbitmq_auth_result = await self.rabbitmq_adapter.test_authentication()
        results.append(
            self._create_test_result(
                test_name="rabbitmq_authentication",
                category=TestCategory.AUTHENTICATION,
                protocol=Protocol.RABBITMQ,
                connection_result=rabbitmq_auth_result
            )
        )
        
        # Test 3: PostgreSQL CoreDB connectivity
        logger.info(f"Testing PostgreSQL CoreDB connectivity for {self.service_name}")
        pg_core_result = await self.pg_core_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="postgresql_coredb_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.POSTGRESQL,
                connection_result=pg_core_result
            )
        )
        
        # Test 4: PostgreSQL CoreDB authentication
        pg_core_auth_result = await self.pg_core_adapter.test_authentication()
        results.append(
            self._create_test_result(
                test_name="postgresql_coredb_authentication",
                category=TestCategory.AUTHENTICATION,
                protocol=Protocol.POSTGRESQL,
                connection_result=pg_core_auth_result
            )
        )
        
        # Test 5: PostgreSQL Gateway connectivity
        logger.info(f"Testing PostgreSQL Gateway connectivity for {self.service_name}")
        pg_gateway_result = await self.pg_gateway_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="postgresql_gateway_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.POSTGRESQL,
                connection_result=pg_gateway_result
            )
        )
        
        # Test 6: Keycloak connectivity
        logger.info(f"Testing Keycloak connectivity for {self.service_name}")
        keycloak_result = await self.keycloak_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="keycloak_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.HTTPS,
                connection_result=keycloak_result
            )
        )
        
        # Test 7: KMS API connectivity
        logger.info(f"Testing KMS API connectivity for {self.service_name}")
        kms_result = await self.kms_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="kms_api_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.HTTP,
                connection_result=kms_result
            )
        )
        
        # Test 8: Search Engine API connectivity
        logger.info(f"Testing Search Engine API connectivity for {self.service_name}")
        search_result = await self.search_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="search_engine_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.ELASTICSEARCH,
                connection_result=search_result
            )
        )
        
        return results
    
    async def run_functional_tests(self) -> List[TestResult]:
        """Run functional tests"""
        results = []
        
        # Test 9: RabbitMQ queue access - core.jobs
        logger.info(f"Testing RabbitMQ queue access for {self.service_name}")
        queue_name = "core.jobs"
        queue_result = await self.rabbitmq_adapter.test_queue_access(queue_name)
        results.append(
            self._create_test_result(
                test_name=f"rabbitmq_queue_{queue_name}",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.RABBITMQ,
                connection_result=queue_result
            )
        )
        
        # Test 10: RabbitMQ publish/consume test
        logger.info(f"Testing RabbitMQ publish/consume for {self.service_name}")
        test_message = {
            "service": "core-api",
            "test": "connectivity_check",
            "timestamp": time.time()
        }
        publish_result = await self.rabbitmq_adapter.test_publish_consume("core.jobs", test_message)
        results.append(
            self._create_test_result(
                test_name="rabbitmq_publish_consume_e2e",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.RABBITMQ,
                connection_result=publish_result
            )
        )
        
        # Test 11: PostgreSQL table access test
        logger.info(f"Testing PostgreSQL table access for {self.service_name}")
        # Common tables in CoreDB
        for table in ["users", "organizations", "roles"]:
            table_result = await self.pg_core_adapter.test_table_access(table)
            results.append(
                self._create_test_result(
                    test_name=f"postgresql_table_{table}",
                    category=TestCategory.FUNCTIONAL,
                    protocol=Protocol.POSTGRESQL,
                    connection_result=table_result
                )
            )
        
        # Test 12: Keycloak health check
        logger.info(f"Testing Keycloak health for {self.service_name}")
        keycloak_health = await self.keycloak_adapter.test_health_check('/health')
        results.append(
            self._create_test_result(
                test_name="keycloak_health_check",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.HTTPS,
                connection_result=keycloak_health
            )
        )
        
        return results
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup adapters"""
        await self.rabbitmq_adapter.close()
        await self.pg_core_adapter.close()
        await self.pg_gateway_adapter.close()
        await self.keycloak_adapter.close()
        await self.kms_adapter.close()
        await self.search_adapter.close()
