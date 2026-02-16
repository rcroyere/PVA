"""
PSO Out Scheduler service test use case
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


class PSOOutSchedulerUseCase(BaseServiceUseCase):
    """
    Test use case for pso-out-scheduler service
    
    Expected flows from matrix:
    - Kafka (Bidirectional, 9092, SASL/TLS) - Communication service
    - PostgreSQL CFK (Event/Async, 5432, TLS) - Communication service
    - HTTP API (8080, mTLS) - sync
    """
    
    def __init__(self, env_config: Dict[str, Any]):
        super().__init__(
            service_name="pso-out-scheduler",
            namespace="cfk-out",
            env_config=env_config
        )
        
        # Initialize adapters
        self.kafka_adapter = KafkaAdapter(env_config.get('kafka', {}))
        self.pg_adapter = PostgreSQLAdapter(env_config.get('postgresql', {}).get('core_db', {}))
        
        # Get service endpoint
        service_config = env_config.get('services', {}).get('pso-out-scheduler', {})
        service_url = f"http://{service_config.get('service_name', 'pso-out-scheduler')}:{service_config.get('port', 8080)}"
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
        
        # Test 4: Service health check
        logger.info(f"Testing HTTP endpoint for {self.service_name}")
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
        
        env = self.env_config.get('environment', 'dev')
        
        # Test 5: Kafka topic bidirectional access
        logger.info(f"Testing Kafka bidirectional topics for {self.service_name}")
        
        # Scheduler typically reads from scheduling topics
        read_topics = [
            f"{env}.out.scheduler.jobs",
            f"{env}.out.scheduler.triggers"
        ]
        
        for topic in read_topics:
            topic_result = await self.kafka_adapter.test_topic_access(topic, 'READ')
            results.append(
                self._create_test_result(
                    test_name=f"kafka_topic_read_{topic}",
                    category=TestCategory.FUNCTIONAL,
                    protocol=Protocol.KAFKA,
                    connection_result=topic_result
                )
            )
        
        # And writes to execution topics
        write_topics = [
            f"{env}.out.scheduler.executions",
            f"{env}.out.processing.exceptions"
        ]
        
        for topic in write_topics:
            topic_result = await self.kafka_adapter.test_topic_access(topic, 'WRITE')
            results.append(
                self._create_test_result(
                    test_name=f"kafka_topic_write_{topic}",
                    category=TestCategory.FUNCTIONAL,
                    protocol=Protocol.KAFKA,
                    connection_result=topic_result
                )
            )
        
        return results
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup adapters"""
        await self.kafka_adapter.close()
        await self.pg_adapter.close()
        await self.http_adapter.close()
