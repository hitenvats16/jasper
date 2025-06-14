import pika
import json
from core.config import settings
import logging
import socket

logger = logging.getLogger(__name__)

class MessagePublisher:
    def __init__(self):
        self.connection = None
        self.channel = None

    def connect(self):
        """Create and return a RabbitMQ connection"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connection = get_rabbitmq_connection()
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=settings.VOICE_PROCESSING_QUEUE, durable=True)
                logger.info("Successfully connected to RabbitMQ")
        except (pika.exceptions.AMQPConnectionError, socket.gaierror) as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def publish(self, queue: str, message: dict):
        """Publish a message to the specified queue"""
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
            logger.info(f"Published message to queue {queue}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message to queue {queue}: {str(e)}")
            raise

    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Create a singleton instance
message_publisher = MessagePublisher()

def get_rabbitmq_connection():
    """Create and return a RabbitMQ connection using connection URL"""
    try:
        # Example URL format: amqp://username:password@hostname:port/vhost
        connection_url = settings.RABBITMQ_URL
        parameters = pika.URLParameters(
            url=connection_url,
        )
        return pika.BlockingConnection(parameters)
    except Exception as e:
        logger.error(f"Failed to create RabbitMQ connection: {str(e)}")
        raise

def publish_voice_job(job_id: int):
    """Publish a voice processing job to RabbitMQ queue"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue=settings.VOICE_PROCESSING_QUEUE, durable=True)
        
        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key=settings.VOICE_PROCESSING_QUEUE,
            body=json.dumps({"job_id": job_id}),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        logger.info(f"Published voice job {job_id} to queue")
        
        # Close connection
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish voice job {job_id}: {str(e)}")
        raise 