"""
Base adapter interface for infrastructure layer
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ConnectionConfig:
    """Base configuration for connections"""
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5


@dataclass
class ConnectionResult:
    """Result of a connection attempt"""
    success: bool
    duration_ms: float
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAdapter(ABC):
    """Base adapter interface"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection_config = ConnectionConfig()
    
    @abstractmethod
    async def test_connectivity(self) -> ConnectionResult:
        """Test basic connectivity"""
        pass
    
    @abstractmethod
    async def test_authentication(self) -> ConnectionResult:
        """Test authentication"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connections"""
        pass
