import pika
import json
import logging
from core.config import settings

logger = logging.getLogger(__name__)

def publish_to_queue(queue_name: str, message: dict):
    """Publish a message to the specified queue without any circular imports"""
    try:
        # Create connection parameters
        parameters = pika.URLParameters(settings.RABBITMQ_URL)
        parameters.socket_timeout = 10.0
        parameters.connection_attempts = 3
        parameters.retry_delay = 1.0
        
        # Create connection and channel
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        logger.info(f"Published message to queue {queue_name}: {message}")
        
        # Close connection
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish message to queue {queue_name}: {str(e)}")
        # Don't raise the exception to avoid breaking the trigger 