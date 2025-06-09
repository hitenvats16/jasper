from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pika
import json
import logging
from core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    def __init__(self, queue_name: str):
        """
        Initialize the worker with a specific queue name.
        
        Args:
            queue_name: The name of the RabbitMQ queue to consume from
        """
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            # Set prefetch count
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"Successfully connected to RabbitMQ queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def process_message(self, ch, method, properties, body):
        """
        Process a message from the queue.
        This is the callback function that RabbitMQ will call when a message is received.
        """
        try:
            message = json.loads(body)
            logger.info(f"Processing message from queue {self.queue_name}: {message}")
            
            # Call the abstract process method
            self.process(message)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Successfully processed message from queue {self.queue_name}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Reject message and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    @abstractmethod
    def process(self, job_data: Dict[str, Any]) -> None:
        """
        Process a job from the RabbitMQ queue.
        This method should be implemented by concrete worker classes.
        
        Args:
            job_data: The job data received from the queue
        """
        pass

    def start(self):
        """Start consuming messages from the queue"""
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message
            )
            logger.info(f"Started consuming messages from queue: {self.queue_name}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error consuming messages: {str(e)}")
            raise

    def close(self):
        """Close the RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")

    def publish_message(self, message: Dict[str, Any]):
        """Publish a message to the queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json',
                    timestamp=int(datetime.utcnow().timestamp())
                )
            )
            logger.info(f"Published message to queue {self.queue_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise 