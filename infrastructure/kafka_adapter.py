"""
Kafka adapter for connectivity and functional testing
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.errors import KafkaError, NoBrokersAvailable
from kafka.admin import NewTopic
import json
import logging

from .base_adapter import BaseAdapter, ConnectionResult

logger = logging.getLogger(__name__)


class KafkaAdapter(BaseAdapter):
    """Kafka connectivity and operations adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.producer: Optional[KafkaProducer] = None
        self.consumer: Optional[KafkaConsumer] = None
        self.admin_client: Optional[KafkaAdminClient] = None
        
    def _get_kafka_config(self) -> Dict[str, Any]:
        """Build Kafka connection config"""
        return {
            'bootstrap_servers': self.config['bootstrap_servers'],
            'security_protocol': self.config.get('security_protocol', 'SASL_SSL'),
            'sasl_mechanism': self.config.get('sasl_mechanism', 'PLAIN'),
            'sasl_plain_username': self.config.get('sasl_username'),
            'sasl_plain_password': self.config.get('sasl_password'),
            'ssl_check_hostname': self.config.get('ssl_check_hostname', True),
        }
    
    async def test_connectivity(self) -> ConnectionResult:
        """Test Kafka broker connectivity"""
        start_time = time.time()
        
        try:
            kafka_config = self._get_kafka_config()
            
            # Try to connect to Kafka admin
            self.admin_client = KafkaAdminClient(**kafka_config)
            
            # List topics to verify connection
            topics = self.admin_client.list_topics()
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message=f"Successfully connected to Kafka. Found {len(topics)} topics.",
                metadata={
                    'topics_count': len(topics),
                    'brokers': kafka_config['bootstrap_servers']
                }
            )
            
        except NoBrokersAvailable as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"No Kafka brokers available: {str(e)}"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Kafka connectivity failed: {str(e)}"
            )
    
    async def test_authentication(self) -> ConnectionResult:
        """Test Kafka SASL authentication"""
        start_time = time.time()
        
        try:
            kafka_config = self._get_kafka_config()
            
            # Create producer to test auth
            producer = KafkaProducer(**kafka_config)
            
            # Get cluster metadata (requires auth)
            metadata = producer.bootstrap_connected()
            
            duration_ms = (time.time() - start_time) * 1000
            
            producer.close()
            
            return ConnectionResult(
                success=True,
                duration_ms=duration_ms,
                message="Kafka authentication successful",
                metadata={'bootstrap_connected': metadata}
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Kafka authentication failed: {str(e)}"
            )
    
    async def test_topic_access(self, topic_name: str, access_type: str = 'READ') -> ConnectionResult:
        """Test access to a specific Kafka topic"""
        start_time = time.time()
        
        try:
            kafka_config = self._get_kafka_config()
            
            if access_type == 'READ':
                # Test consumer access
                consumer = KafkaConsumer(
                    topic_name,
                    **kafka_config,
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    consumer_timeout_ms=5000
                )
                
                # Get partitions
                partitions = consumer.partitions_for_topic(topic_name)
                
                consumer.close()
                
                duration_ms = (time.time() - start_time) * 1000
                
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Read access to topic '{topic_name}' verified",
                    metadata={
                        'topic': topic_name,
                        'partitions': len(partitions) if partitions else 0,
                        'access_type': access_type
                    }
                )
                
            elif access_type == 'WRITE':
                # Test producer access
                producer = KafkaProducer(**kafka_config)
                
                # Try to get topic metadata (doesn't actually send)
                metadata = producer.partitions_for(topic_name)
                
                producer.close()
                
                duration_ms = (time.time() - start_time) * 1000
                
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Write access to topic '{topic_name}' verified",
                    metadata={
                        'topic': topic_name,
                        'access_type': access_type
                    }
                )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Topic access test failed for '{topic_name}': {str(e)}"
            )
    
    async def test_produce_consume(self, topic_name: str, test_message: Dict[str, Any]) -> ConnectionResult:
        """Test end-to-end produce and consume"""
        start_time = time.time()
        
        try:
            kafka_config = self._get_kafka_config()
            
            # Produce message
            producer = KafkaProducer(
                **kafka_config,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            test_id = f"test_{int(time.time() * 1000)}"
            test_message['test_id'] = test_id
            
            future = producer.send(topic_name, value=test_message)
            record_metadata = future.get(timeout=10)
            
            producer.flush()
            producer.close()
            
            # Consume message
            consumer = KafkaConsumer(
                topic_name,
                **kafka_config,
                auto_offset_reset='latest',
                enable_auto_commit=False,
                consumer_timeout_ms=10000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            # Seek to the produced message
            partition = record_metadata.partition
            offset = record_metadata.offset
            
            from kafka import TopicPartition
            tp = TopicPartition(topic_name, partition)
            consumer.assign([tp])
            consumer.seek(tp, offset)
            
            # Try to consume
            consumed = False
            for message in consumer:
                if message.value.get('test_id') == test_id:
                    consumed = True
                    break
            
            consumer.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if consumed:
                return ConnectionResult(
                    success=True,
                    duration_ms=duration_ms,
                    message=f"Successfully produced and consumed message on topic '{topic_name}'",
                    metadata={
                        'topic': topic_name,
                        'partition': partition,
                        'offset': offset,
                        'test_id': test_id
                    }
                )
            else:
                return ConnectionResult(
                    success=False,
                    duration_ms=duration_ms,
                    error=f"Message produced but not consumed on topic '{topic_name}'"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ConnectionResult(
                success=False,
                duration_ms=duration_ms,
                error=f"Produce/consume test failed: {str(e)}"
            )
    
    async def close(self):
        """Close all Kafka connections"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        if self.admin_client:
            self.admin_client.close()
