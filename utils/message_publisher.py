import pika
import json
from core.config import settings
import logging
import socket

from services.book_processing_service import BookProcessingService
from db.session import SessionLocal

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
    """Create and return a RabbitMQ connection using connection URL with timeout"""
    try:
        # Example URL format: amqp://username:password@hostname:port/vhost
        connection_url = settings.RABBITMQ_URL
        parameters = pika.URLParameters(
            url=connection_url,
        )
        # Add timeout settings
        parameters.socket_timeout = 10.0  # 10 second timeout
        parameters.connection_attempts = 3  # Retry 3 times
        parameters.retry_delay = 1.0  # 1 second between retries
        
        return pika.BlockingConnection(parameters)
    except Exception as e:
        logger.error(f"Failed to create RabbitMQ connection: {str(e)}")
        raise

def create_book_processing_job(book_id):
    """Create a BookProcessingJob for the newly created book"""
    try:
        logger.info(f"Starting job creation for book_id: {book_id} (type: {type(book_id)})")
        
        # Validate input
        if not isinstance(book_id, int):
            logger.error(f"Expected book_id to be an integer, got {type(book_id)}: {book_id}")
            return
        
        # Get a database session
        db = SessionLocal()
        
        try:
            # Import Book model
            from models.book import Book
            logger.info("Successfully imported Book model")
            
            # Get the book object from the database
            logger.info(f"Querying for book with ID: {book_id}")
            book = db.query(Book).filter(Book.id == book_id, Book.is_deleted == False).first()
            
            if not book:
                logger.error(f"Book with ID {book_id} not found in database")
                return
            
            logger.info(f"Found book: {book.title} (ID: {book.id}, type: {type(book)})")
            
            # Validate book object
            if not hasattr(book, 'id'):
                logger.error(f"Book object doesn't have 'id' attribute. Type: {type(book)}, Dir: {dir(book)}")
                return
                
            if not hasattr(book, 'user_id'):
                logger.error(f"Book object doesn't have 'user_id' attribute. Type: {type(book)}, Dir: {dir(book)}")
                return
            
            # Create the processing job using the service
            logger.info("Creating BookProcessingService instance")
            book_service = BookProcessingService()
            
            logger.info(f"Calling create_and_publish_job with book object (ID: {book.id})")
            job = book_service.create_and_publish_job(db, book)
            
            if job:
                logger.info(f"Successfully created and published job {job.id} for book {book_id}")
            else:
                logger.error(f"Failed to create job for book {book_id} - service returned None")
        
        except Exception as e:
            logger.error(f"Error in create_book_processing_job: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            try:
                db.close()
                logger.info("Database session closed")
            except Exception as e:
                logger.error(f"Error closing database session: {str(e)}")
        
    except Exception as e:
        logger.error(f"Failed to create BookProcessingJob for book {book_id}: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Don't fail the book creation if job creation fails

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

def publish_message(queue_name: str, message: str):
    """Publish a message to the specified queue"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        logger.info(f"Published message to queue {queue_name}")
        
        # Close connection
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish message to queue {queue_name}: {str(e)}")
        raise 