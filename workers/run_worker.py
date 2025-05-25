import pika
import json
import logging
from core.config import settings
from workers.voice_processing import VoiceProcessingWorker
import signal
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

def process_message(ch, method, properties, body):
    """Callback function for processing RabbitMQ messages"""
    try:
        job_data = json.loads(body)
        worker = VoiceProcessingWorker()
        worker.process(job_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Reject the message and requeue it
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    """Main function to run the worker"""
    try:
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal. Cleaning up...")
            if connection and not connection.is_closed:
                connection.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Connect to RabbitMQ
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        # Ensure queue exists
        channel.queue_declare(queue=settings.VOICE_PROCESSING_QUEUE, durable=True)

        # Set up consumer
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=settings.VOICE_PROCESSING_QUEUE,
            on_message_callback=process_message
        )

        logger.info("Worker started. Waiting for messages...")
        channel.start_consuming()

    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        if 'connection' in locals() and not connection.is_closed:
            connection.close()
        sys.exit(1)

if __name__ == "__main__":
    main() 