from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pika
import json
import logging
from core.config import settings
from datetime import datetime
from models import User, VoiceProcessingJob, Voice  # Import models to ensure they're initialized

logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    def __init__(self, queue_name: str, max_retries: int = 3):
        """
        Initialize the worker with a specific queue name.
        
        Args:
            queue_name: The name of the RabbitMQ queue to consume from
            max_retries: Maximum number of retry attempts before rejecting message permanently
        """
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            connection_url = settings.RABBITMQ_URL
            parameters = pika.URLParameters(
                url=connection_url
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            # Declare dead letter queue for failed messages
            dead_letter_queue = f"{self.queue_name}_dead_letter"
            self.channel.queue_declare(
                queue=dead_letter_queue,
                durable=True
            )
            
            # Set prefetch count
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"Successfully connected to RabbitMQ queue: {self.queue_name}")
            logger.info(f"Dead letter queue created: {dead_letter_queue}")
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
            
            # Get retry count from message headers
            retry_count = 0
            if properties.headers:
                retry_count = properties.headers.get('x-retry-count', 0)
            
            if retry_count < self.max_retries:
                # Increment retry count and requeue
                retry_count += 1
                logger.warning(f"Requeuing message (attempt {retry_count}/{self.max_retries})")
                
                # Update headers with retry count
                new_headers = properties.headers.copy() if properties.headers else {}
                new_headers['x-retry-count'] = retry_count
                new_headers['x-first-failure-time'] = new_headers.get('x-first-failure-time', datetime.utcnow().isoformat())
                new_headers['x-last-failure-time'] = datetime.utcnow().isoformat()
                new_headers['x-last-error'] = str(e)[:500]  # Truncate long error messages
                
                # Republish with updated headers
                ch.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=body,
                    properties=pika.BasicProperties(
                        headers=new_headers,
                        delivery_mode=2
                    )
                )
                
                # Acknowledge original message to remove it from queue
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Max retries reached, send to dead letter queue
                logger.error(f"Max retries ({self.max_retries}) reached for message. Moving to dead letter queue.")
                dead_letter_queue = f"{self.queue_name}_dead_letter"
                
                # Add failure metadata to headers
                final_headers = properties.headers.copy() if properties.headers else {}
                final_headers['x-final-failure-time'] = datetime.utcnow().isoformat()
                final_headers['x-final-error'] = str(e)[:500]
                final_headers['x-total-retries'] = retry_count
                
                # Send to dead letter queue
                ch.basic_publish(
                    exchange='',
                    routing_key=dead_letter_queue,
                    body=body,
                    properties=pika.BasicProperties(
                        headers=final_headers,
                        delivery_mode=2
                    )
                )
                
                # Acknowledge original message to remove it from queue
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Message moved to dead letter queue: {dead_letter_queue}")

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