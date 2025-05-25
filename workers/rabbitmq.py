import pika
import json
from core.config import settings
from typing import Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self):
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
            self.channel.queue_declare(queue=settings.VOICE_PROCESSING_QUEUE, durable=True)
            logger.info("Successfully connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def publish_message(self, queue: str, message: Dict[str, Any]):
        """Publish a message to a queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    def consume_messages(self, queue: str, callback: Callable):
        """Start consuming messages from a queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=callback
            )
            logger.info(f"Started consuming messages from queue: {queue}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to consume messages: {str(e)}")
            raise

    def close(self):
        """Close the RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection") 