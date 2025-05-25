import pika
import json
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_rabbitmq_connection():
    """Create and return a RabbitMQ connection"""
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
    return pika.BlockingConnection(parameters)

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