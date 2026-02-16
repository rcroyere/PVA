"""Infrastructure adapters package"""

from .base_adapter import BaseAdapter, ConnectionResult, ConnectionConfig
from .kafka_adapter import KafkaAdapter
from .rabbitmq_adapter import RabbitMQAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .http_adapter import HTTPAdapter
from .sftp_adapter import SFTPAdapter

__all__ = [
    'BaseAdapter',
    'ConnectionResult',
    'ConnectionConfig',
    'KafkaAdapter',
    'RabbitMQAdapter',
    'PostgreSQLAdapter',
    'HTTPAdapter',
    'SFTPAdapter',
]
