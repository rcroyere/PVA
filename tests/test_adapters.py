"""
Unit tests for infrastructure adapters
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from infrastructure.kafka_adapter import KafkaAdapter
from infrastructure.rabbitmq_adapter import RabbitMQAdapter
from infrastructure.postgresql_adapter import PostgreSQLAdapter
from infrastructure.http_adapter import HTTPAdapter


class TestKafkaAdapter:
    """Tests for Kafka adapter"""
    
    @pytest.fixture
    def kafka_config(self):
        return {
            'bootstrap_servers': ['localhost:9092'],
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'PLAIN',
            'sasl_username': 'test_user',
            'sasl_password': 'test_pass'
        }
    
    @pytest.fixture
    def kafka_adapter(self, kafka_config):
        return KafkaAdapter(kafka_config)
    
    @pytest.mark.asyncio
    async def test_connectivity_success(self, kafka_adapter):
        """Test successful Kafka connectivity"""
        with patch('kafka.KafkaAdminClient') as mock_admin:
            mock_admin.return_value.list_topics.return_value = ['topic1', 'topic2']
            
            result = await kafka_adapter.test_connectivity()
            
            assert result.success is True
            assert result.duration_ms > 0
            assert 'topics_count' in result.metadata
            assert result.metadata['topics_count'] == 2
    
    @pytest.mark.asyncio
    async def test_connectivity_failure(self, kafka_adapter):
        """Test failed Kafka connectivity"""
        with patch('kafka.KafkaAdminClient') as mock_admin:
            mock_admin.side_effect = Exception("Connection failed")
            
            result = await kafka_adapter.test_connectivity()
            
            assert result.success is False
            assert result.error is not None
            assert 'Connection failed' in result.error
    
    @pytest.mark.asyncio
    async def test_topic_access_read(self, kafka_adapter):
        """Test Kafka topic read access"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_instance = Mock()
            mock_instance.partitions_for_topic.return_value = {0, 1, 2}
            mock_consumer.return_value = mock_instance
            
            result = await kafka_adapter.test_topic_access('test-topic', 'READ')
            
            assert result.success is True
            assert result.metadata['topic'] == 'test-topic'
            assert result.metadata['partitions'] == 3


class TestRabbitMQAdapter:
    """Tests for RabbitMQ adapter"""
    
    @pytest.fixture
    def rabbitmq_config(self):
        return {
            'host': 'localhost',
            'port': 5672,
            'vhost': '/',
            'username': 'guest',
            'password': 'guest',
            'ssl': False
        }
    
    @pytest.fixture
    def rabbitmq_adapter(self, rabbitmq_config):
        return RabbitMQAdapter(rabbitmq_config)
    
    @pytest.mark.asyncio
    async def test_connectivity_success(self, rabbitmq_adapter):
        """Test successful RabbitMQ connectivity"""
        with patch('pika.BlockingConnection') as mock_conn:
            mock_instance = Mock()
            mock_instance.server_properties = {'version': '3.11.0'}
            mock_conn.return_value = mock_instance
            
            result = await rabbitmq_adapter.test_connectivity()
            
            assert result.success is True
            assert result.metadata['server_version'] == '3.11.0'
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, rabbitmq_adapter):
        """Test failed RabbitMQ authentication"""
        import pika.exceptions
        
        with patch('pika.BlockingConnection') as mock_conn:
            mock_conn.side_effect = pika.exceptions.ProbableAuthenticationError()
            
            result = await rabbitmq_adapter.test_authentication()
            
            assert result.success is False
            assert 'authentication failed' in result.error.lower()


class TestPostgreSQLAdapter:
    """Tests for PostgreSQL adapter"""
    
    @pytest.fixture
    def pg_config(self):
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'testuser',
            'password': 'testpass',
            'ssl_mode': 'require'
        }
    
    @pytest.fixture
    def pg_adapter(self, pg_config):
        return PostgreSQLAdapter(pg_config)
    
    @pytest.mark.asyncio
    async def test_connectivity_success(self, pg_adapter):
        """Test successful PostgreSQL connectivity"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ('PostgreSQL 14.5',)
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = await pg_adapter.test_connectivity()
            
            assert result.success is True
            assert 'PostgreSQL 14.5' in result.metadata['version']
    
    @pytest.mark.asyncio
    async def test_table_access(self, pg_adapter):
        """Test PostgreSQL table access"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = False
            mock_cursor = Mock()
            mock_cursor.fetchone.side_effect = [
                (True,),  # Table exists
                (100,)    # Row count
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            pg_adapter.connection = mock_conn
            result = await pg_adapter.test_table_access('users')
            
            assert result.success is True
            assert result.metadata['table'] == 'users'
            assert result.metadata['row_count'] == 100


class TestHTTPAdapter:
    """Tests for HTTP adapter"""
    
    @pytest.fixture
    def http_config(self):
        return {
            'base_url': 'http://localhost:8080',
            'verify_ssl': False
        }
    
    @pytest.fixture
    def http_adapter(self, http_config):
        return HTTPAdapter(http_config)
    
    @pytest.mark.asyncio
    async def test_connectivity_success(self, http_adapter):
        """Test successful HTTP connectivity"""
        with patch('requests.Session.head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/json'}
            mock_head.return_value = mock_response
            
            result = await http_adapter.test_connectivity()
            
            assert result.success is True
            assert result.metadata['status_code'] == 200
    
    @pytest.mark.asyncio
    async def test_health_check(self, http_adapter):
        """Test HTTP health check endpoint"""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'healthy'}
            mock_get.return_value = mock_response
            
            result = await http_adapter.test_health_check('/health')
            
            assert result.success is True
            assert result.metadata['health_data']['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_connectivity_timeout(self, http_adapter):
        """Test HTTP connectivity timeout"""
        import requests.exceptions
        
        with patch('requests.Session.head') as mock_head:
            mock_head.side_effect = requests.exceptions.Timeout()
            
            result = await http_adapter.test_connectivity()
            
            assert result.success is False
            assert 'timeout' in result.error.lower()


# Run tests with: pytest tests/test_adapters.py -v
