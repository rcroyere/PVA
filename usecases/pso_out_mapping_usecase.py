"""
PSO Out Mapping service test use case
Based on flux matrix - CFK services
"""
import time
from typing import List, Dict, Any
import logging

from usecases.base_usecase import BaseServiceUseCase
from models import TestResult, TestCategory, Protocol
from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter

logger = logging.getLogger(__name__)


class PSOOutMappingUseCase(BaseServiceUseCase):
    """
    Test use case for pso-out-mapping service
    
    Expected flows from matrix:
    - PostgreSQL CFK (Bidirectional, 5432, TLS) - Event/Async
    - Kafka (Sortant, 9092, SASL/TLS) - Communication service
    - Azure Blob Storage S3 (Sortant)
    - HTTP API (8080, mTLS) - sync
    """
    
    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="pso-out-mapping",
            namespace="cfk-out",
            env_config=env_config
        )
        
        # Initialize adapters
        self.kafka_adapter = KafkaAdapter(env_config.get('kafka', {}))
        self.pg_adapter = PostgreSQLAdapter(env_config.get('postgresql', {}).get('core_db', {}))
        
        # Get service endpoint
        service_config = env_config.get('services', {}).get('pso-out-mapping', {})
        service_url = f"http://{service_config.get('service_name', 'pso-out-mapping')}:{service_config.get('port', 8080)}"
        self.http_adapter = HTTPAdapter({'base_url': service_url})
    
    async def run_connectivity_tests(self) -> List[TestResult]:
        """Run connectivity tests"""
        results = []
        
        # Test 1: Kafka connectivity
        logger.info(f"Testing Kafka connectivity for {self.service_name}")
        kafka_result = await self.kafka_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="kafka_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.KAFKA,
                connection_result=kafka_result
            )
        )
        
        # Test 2: Kafka authentication
        kafka_auth_result = await self.kafka_adapter.test_authentication()
        results.append(
            self._create_test_result(
                test_name="kafka_authentication",
                category=TestCategory.AUTHENTICATION,
                protocol=Protocol.KAFKA,
                connection_result=kafka_auth_result
            )
        )
        
        # Test 3: PostgreSQL connectivity
        logger.info(f"Testing PostgreSQL connectivity for {self.service_name}")
        pg_result = await self.pg_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="postgresql_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.POSTGRESQL,
                connection_result=pg_result
            )
        )
        
        # Test 4: PostgreSQL authentication
        pg_auth_result = await self.pg_adapter.test_authentication()
        results.append(
            self._create_test_result(
                test_name="postgresql_authentication",
                category=TestCategory.AUTHENTICATION,
                protocol=Protocol.POSTGRESQL,
                connection_result=pg_auth_result
            )
        )
        
        # Test 5: Service HTTP endpoint
        logger.info(f"Testing HTTP endpoint for {self.service_name}")
        http_result = await self.http_adapter.test_connectivity()
        results.append(
            self._create_test_result(
                test_name="http_connectivity",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.HTTP,
                connection_result=http_result
            )
        )
        
        # Test 6: Service health check
        health_result = await self.http_adapter.test_health_check()
        results.append(
            self._create_test_result(
                test_name="health_check",
                category=TestCategory.CONNECTIVITY,
                protocol=Protocol.HTTP,
                connection_result=health_result
            )
        )
        
        return results
    
    async def run_functional_tests(self) -> List[TestResult]:
        """Run functional tests"""
        results = []
        
        # Get environment prefix (dev/qa/pp/prod)
        env = self.env_config.get('environment', 'dev')
        
        # Test 7: Kafka topic read access - backoffice.in.request.data.json
        logger.info(f"Testing Kafka topic READ access for {self.service_name}")
        topic_name = f"{env}.backoffice.in.request.data.json"
        topic_read_result = await self.kafka_adapter.test_topic_access(topic_name, 'READ')
        results.append(
            self._create_test_result(
                test_name=f"kafka_topic_read_{topic_name}",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.KAFKA,
                connection_result=topic_read_result
            )
        )
        
        # Test 8: Kafka topic read access - out.cdc.field.related.json
        topic_name = f"{env}.out.cdc.field.related.json"
        topic_read_result = await self.kafka_adapter.test_topic_access(topic_name, 'READ')
        results.append(
            self._create_test_result(
                test_name=f"kafka_topic_read_{topic_name}",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.KAFKA,
                connection_result=topic_read_result
            )
        )
        
        # Test 9: Kafka topic write access - out.cdc.field.related.json-dlt
        logger.info(f"Testing Kafka topic WRITE access for {self.service_name}")
        topic_name = f"{env}.out.cdc.field.related.json-dlt"
        topic_write_result = await self.kafka_adapter.test_topic_access(topic_name, 'WRITE')
        results.append(
            self._create_test_result(
                test_name=f"kafka_topic_write_{topic_name}",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.KAFKA,
                connection_result=topic_write_result
            )
        )
        
        # Test 10: Kafka topic write access - out.processing.exceptions
        topic_name = f"{env}.out.processing.exceptions"
        topic_write_result = await self.kafka_adapter.test_topic_access(topic_name, 'WRITE')
        results.append(
            self._create_test_result(
                test_name=f"kafka_topic_write_{topic_name}",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.KAFKA,
                connection_result=topic_write_result
            )
        )
        
        # Test 11: End-to-end Kafka produce/consume test
        logger.info(f"Testing Kafka produce/consume for {self.service_name}")
        test_topic = f"{env}.out.processing.exceptions"
        test_message = {
            "service": "pso-out-mapping",
            "test": "connectivity_check",
            "timestamp": time.time()
        }
        produce_consume_result = await self.kafka_adapter.test_produce_consume(test_topic, test_message)
        results.append(
            self._create_test_result(
                test_name="kafka_produce_consume_e2e",
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.KAFKA,
                connection_result=produce_consume_result
            )
        )
        
        return results
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup adapters"""
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
        await self.http_adapter.close()
