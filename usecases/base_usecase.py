"""
Base use case for service testing
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
from datetime import datetime

from models import TestResult, ServiceTestSuite, TestStatus, TestCategory, Protocol

logger = logging.getLogger(__name__)


class BaseServiceUseCase(ABC):
    """Base class for service test use cases"""
    
    def __init__(self, service_name: str, namespace: str, env_config: Dict[str, Any]):
        self.service_name = service_name
        self.namespace = namespace
        self.env_config = env_config
        self.test_suite = ServiceTestSuite(
            service_name=service_name,
            namespace=namespace
        )
    
    @abstractmethod
    async def run_connectivity_tests(self) -> List[TestResult]:
        """Run connectivity tests for this service"""
        pass
    
    @abstractmethod
    async def run_functional_tests(self) -> List[TestResult]:
        """Run functional tests for this service"""
        pass
    
    async def run_all_tests(self) -> ServiceTestSuite:
        """Run all tests for this service"""
        logger.info(f"Starting tests for service: {self.service_name}")
        
        self.test_suite.started_at = datetime.utcnow()
        
        try:
            # Run connectivity tests
            connectivity_results = await self.run_connectivity_tests()
            self.test_suite.results.extend(connectivity_results)
            
            # Run functional tests
            functional_results = await self.run_functional_tests()
            self.test_suite.results.extend(functional_results)
            
        except Exception as e:
            logger.error(f"Error running tests for {self.service_name}: {e}")
            # Add error result
            error_result = TestResult(
                test_name="test_suite_execution",
                service_name=self.service_name,
                category=TestCategory.FUNCTIONAL,
                protocol=Protocol.HTTP,
                status=TestStatus.ERROR,
                duration_ms=0,
                error=str(e)
            )
            self.test_suite.results.append(error_result)
        
        finally:
            self.test_suite.completed_at = datetime.utcnow()
        
        logger.info(
            f"Tests completed for {self.service_name}: "
            f"{self.test_suite.passed_count}/{self.test_suite.total_count} passed"
        )
        
        return self.test_suite
    
    def _create_test_result(
        self,
        test_name: str,
        category: TestCategory,
        protocol: Protocol,
        connection_result,
        metadata: Dict[str, Any] = None
    ) -> TestResult:
        """Helper to create a TestResult from ConnectionResult"""
        
        status = TestStatus.PASSED if connection_result.success else TestStatus.FAILED
        
        result_metadata = connection_result.metadata.copy()
        if metadata:
            result_metadata.update(metadata)
        
        return TestResult(
            test_name=test_name,
            service_name=self.service_name,
            category=category,
            protocol=protocol,
            status=status,
            duration_ms=connection_result.duration_ms,
            message=connection_result.message,
            error=connection_result.error,
            metadata=result_metadata
        )
