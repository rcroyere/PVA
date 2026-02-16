"""
Base models for test execution and reporting
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any


class TestStatus(Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCategory(Enum):
    """Test category types"""
    CONNECTIVITY = "connectivity"
    AUTHENTICATION = "authentication"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"


class Protocol(Enum):
    """Communication protocols"""
    HTTP = "http"
    HTTPS = "https"
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    SFTP = "sftp"
    MEMCACHED = "memcached"


@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    service_name: str
    category: TestCategory
    protocol: Protocol
    status: TestStatus
    duration_ms: float
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "test_name": self.test_name,
            "service_name": self.service_name,
            "category": self.category.value,
            "protocol": self.protocol.value,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ServiceTestSuite:
    """Collection of tests for a service"""
    service_name: str
    namespace: str
    results: List[TestResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)
    
    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)
    
    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
    
    @property
    def total_count(self) -> int:
        return len(self.results)
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_count == 0:
            return 0.0
        return (self.passed_count / self.total_count) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "service_name": self.service_name,
            "namespace": self.namespace,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "total_tests": self.total_count,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "errors": self.error_count,
            "skipped": self.skipped_count,
            "success_rate": self.success_rate,
            "results": [r.to_dict() for r in self.results]
        }


@dataclass
class TestExecutionReport:
    """Overall test execution report"""
    environment: str
    execution_id: str
    suites: List[ServiceTestSuite] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def total_duration_seconds(self) -> float:
        """Total execution duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def total_tests(self) -> int:
        return sum(suite.total_count for suite in self.suites)
    
    @property
    def total_passed(self) -> int:
        return sum(suite.passed_count for suite in self.suites)
    
    @property
    def total_failed(self) -> int:
        return sum(suite.failed_count for suite in self.suites)
    
    @property
    def total_errors(self) -> int:
        return sum(suite.error_count for suite in self.suites)
    
    @property
    def overall_success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "environment": self.environment,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_seconds": self.total_duration_seconds,
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.total_passed,
                "failed": self.total_failed,
                "errors": self.total_errors,
                "success_rate": self.overall_success_rate
            },
            "suites": [suite.to_dict() for suite in self.suites]
        }
