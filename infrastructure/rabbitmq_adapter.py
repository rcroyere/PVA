"""
RabbitMQ adapter for connectivity and functional testing
"""
import time
import asyncio
import pika
import json
from typing import Dict, Any, Optional
import logging

from .base_adapter import BaseAdapter, ConnectionResult

logger = logging.getLogger(__name__)


class RabbitMQAdapter(BaseAdapter):
    """RabbitMQ connectivity and operations adapter"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None

        # kubectl mode: test from within the pod via kubectl exec
        self._kubectl = config.get('_kubectl')
        if self._kubectl:
            self._kube_host = self.config.get('host', 'localhost')
            self._kube_port = int(self.config.get('port', 5672))
    
    def _get_connection_params(self) -> pika.ConnectionParameters:
        """Build RabbitMQ connection parameters"""
        credentials = pika.PlainCredentials(
            username=self.config.get('username'),
            password=self.config.get('password')
        )
        
        ssl_options = None
        if self.config.get('ssl', False):
            ssl_options = pika.SSLOptions()
        
        return pika.ConnectionParameters(
            host=self.config.get('host'),
            port=self.config.get('port', 5672),
            virtual_host=self.config.get('vhost', '/'),
            credentials=credentials,
            ssl_options=ssl_options,
            heartbeat=600,
            blocked_connection_timeout=300
        )
    
    async def test_connectivity(self) -> ConnectionResult:
        """Test RabbitMQ broker connectivity"""
        if self._kubectl:
            return await self._kubectl['executor'].test_tcp(
                self._kubectl['namespace'], self._kubectl['pod'],
                self._kube_host, self._kube_port
            )

        start_time = time.time()

        try:
            params = self._get_connection_params()
            
            # Establish connection
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Get server properties
            server_props = self.connection.server_properties if self.connection else {}
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Successfully connected to RabbitMQ at {self.config.get('host')}",
                metadata={
                    'host': self.config.get('host'),
                    'vhost': self.config.get('vhost', '/'),
                    'server_version': server_props.get('version', 'unknown')
                }
            )
            
        except pika.exceptions.AMQPConnectionError as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"RabbitMQ connection failed: {str(e)}"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"RabbitMQ connectivity test failed: {str(e)}"
            )
    
    async def test_authentication(self) -> ConnectionResult:
        """Test RabbitMQ authentication"""
        if self._kubectl:
            result = await self.test_connectivity()
            result.metadata['note'] = 'authentication not testable in kubectl mode (no AMQP client in pod)'
            return result

        start_time = time.time()

        try:
            params = self._get_connection_params()

            # Try to connect with credentials
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            
            # Verify permissions by trying to declare a queue
            queue_name = f"test_auth_{int(time.time())}"
            channel.queue_declare(queue=queue_name, passive=False, durable=False, auto_delete=True)
            channel.queue_delete(queue=queue_name)
            
            duration_ms = (time.time() - start_time) * 1000
            
            connection.close()
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message="RabbitMQ authentication successful",
                metadata={
                    'username': self.config.get('username'),
                    'vhost': self.config.get('vhost', '/')
                }
            )
            
        except pika.exceptions.ProbableAuthenticationError as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"RabbitMQ authentication failed: {str(e)}"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"RabbitMQ authentication test failed: {str(e)}"
            )
    
    async def test_queue_access(self, queue_name: str) -> ConnectionResult:
        """Test access to a specific queue"""
        if self._kubectl:
            return ConnectionResult(
                success=True,
                duration_ms=0,
                message=f"Queue access test skipped in kubectl mode (no AMQP client in pod)",
                metadata={'mode': 'kubectl', 'queue': queue_name}
            )

        start_time = time.time()

        try:
            if not self.connection or self.connection.is_closed:
                await self.test_connectivity()
            
            # Check if queue exists
            try:
                self.channel.queue_declare(queue=queue_name, passive=True)
                exists = True
            except pika.exceptions.ChannelClosedByBroker:
                exists = False
                # Reopen channel
                self.channel = self.connection.channel()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if exists:
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Queue '{queue_name}' is accessible",
                    metadata={'queue': queue_name, 'exists': True}
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Queue '{queue_name}' does not exist or is not accessible"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Queue access test failed for '{queue_name}': {str(e)}"
            )
    
    async def test_publish_consume(self, queue_name: str, test_message: Dict[str, Any]) -> ConnectionResult:
        """Test end-to-end publish and consume"""
        if self._kubectl:
            return ConnectionResult(
                success=True,
                duration_ms=0,
                message=f"Publish/consume test skipped in kubectl mode (no AMQP client in pod)",
                metadata={'mode': 'kubectl', 'queue': queue_name}
            )

        start_time = time.time()

        try:
            if not self.connection or self.connection.is_closed:
                await self.test_connectivity()
            
            # Declare temporary queue for testing
            test_queue = f"test_{queue_name}_{int(time.time())}"
            self.channel.queue_declare(queue=test_queue, auto_delete=True, durable=False)
            
            # Publish message
            test_id = f"test_{int(time.time() * 1000)}"
            test_message['test_id'] = test_id
            
            self.channel.basic_publish(
                exchange='',
                routing_key=test_queue,
                body=json.dumps(test_message),
                properties=pika.BasicProperties(
                    delivery_mode=1,  # Non-persistent
                    content_type='application/json'
                )
            )
            
            # Consume message
            method_frame, header_frame, body = self.channel.basic_get(queue=test_queue, auto_ack=True)
            
            consumed = False
            if method_frame:
                received_message = json.loads(body.decode('utf-8'))
                if received_message.get('test_id') == test_id:
                    consumed = True
            
            # Cleanup
            self.channel.queue_delete(queue=test_queue)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if consumed:
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Successfully published and consumed message on queue '{test_queue}'",
                    metadata={
                        'queue': test_queue,
                        'test_id': test_id
                    }
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Message published but not consumed on queue '{test_queue}'"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Publish/consume test failed: {str(e)}"
            )
    
    async def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.warning(f"Error closing RabbitMQ connection: {e}")
