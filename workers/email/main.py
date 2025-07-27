import logging
import json
import sys
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from db.session import get_db
from models.user import User
from workers.base import BaseWorker
from .templates import EmailType, template_manager
from core.config import settings
import resend
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

class EmailWorker(BaseWorker):
    """
    Worker for sending transactional emails via Resend.
    
    Expected job data format:
    {
        "user_id": int,
        "email_type": str,  # One of EmailType enum values
        "email_data": dict  # Data to populate the email template
    }
    """
    
    def __init__(self):
        logger.info(f"Initializing EmailWorker with queue: email_queue")
        super().__init__(queue_name="email_queue", max_retries=3)
        self._setup_resend()
        logger.info("EmailWorker initialized successfully")
    
    def _setup_resend(self):
        """Setup Resend client"""
        try:
            if not hasattr(settings, 'RESEND_API_KEY'):
                raise ValueError("RESEND_API_KEY not configured in settings")
            
            resend.api_key = settings.RESEND_API_KEY
            logger.info("Resend client configured successfully")
        except Exception as e:
            logger.error(f"Failed to setup Resend client: {str(e)}")
            raise
    
    def process(self, job_data: Dict[str, Any]) -> None:
        """
        Process an email job from the queue.
        
        Args:
            job_data: Dictionary containing user_id, email_type, and email_data
        """
        logger.info(f"Processing email job: {job_data}")
        
        try:
            # Validate job data
            required_fields = ["user_id", "email_type", "email_data"]
            for field in required_fields:
                if field not in job_data:
                    logger.error(f"Missing required field in job data: {field}")
                    raise ValueError(f"Missing required field: {field}")
            
            user_id = job_data["user_id"]
            email_type_str = job_data["email_type"]
            email_data = job_data["email_data"]
            
            logger.info(f"Processing email job for user {user_id}, type: {email_type_str}")
            logger.info(f"Email data: {email_data}")
            
            # Validate email type
            try:
                email_type = EmailType(email_type_str)
                logger.info(f"Validated email type: {email_type.value}")
            except ValueError as e:
                logger.error(f"Invalid email type '{email_type_str}': {str(e)}")
                raise ValueError(f"Invalid email type: {email_type_str}")
            
            # Get user from database
            logger.info(f"Fetching user {user_id} from database")
            db = next(get_db())
            user = self._get_user(db, user_id)
            if not user:
                logger.error(f"User {user_id} not found in database")
                raise ValueError(f"User not found with ID: {user_id}")
            
            logger.info(f"Found user: {user.email} (ID: {user.id})")
            
            # Send email
            logger.info(f"Preparing to send {email_type.value} email to {user.email}")
            self._send_email(user, email_type, email_data)
            
            logger.info(f"Successfully sent {email_type.value} email to user {user_id} ({user.email})")
            
        except Exception as e:
            logger.error(f"Failed to process email job: {str(e)}")
            logger.error(f"Job data: {job_data}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _get_user(self, db: Session, user_id: int) -> Optional[User]:
        """Get user from database"""
        try:
            logger.debug(f"Querying database for user {user_id}")
            user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
            
            if user:
                logger.debug(f"Found user: {user.email} (ID: {user.id}, Active: {user.is_active})")
            else:
                logger.warning(f"User {user_id} not found or is deleted")
                
            return user
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching user {user_id}: {str(e)}")
            logger.error(f"SQLAlchemy error details: {traceback.format_exc()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching user {user_id}: {str(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            return None
    
    def _send_email(self, user: User, email_type: EmailType, email_data: Dict[str, Any]):
        """
        Send email to user using Resend.
        
        Args:
            user: User object
            email_type: Type of email to send
            email_data: Data to populate the email template
        """
        logger.info(f"Starting email send process for {user.email}")
        
        try:
            # Prepare email data with user information
            logger.debug("Preparing template data")
            template_data = self._prepare_template_data(user, email_data)
            logger.debug(f"Template data prepared: {template_data}")
            
            # Render email template
            logger.debug(f"Rendering email template for type: {email_type.value}")
            html_content, text_content = template_manager.render_template(email_type, template_data)
            logger.debug(f"Email template rendered successfully. HTML length: {len(html_content)}, Text length: {len(text_content)}")
            
            # Get email subject
            subject = template_manager.get_template(email_type).subject
            logger.info(f"Email subject: {subject}")
            
            # Prepare email payload
            email_payload = {
                "from": settings.EMAILS_FROM_EMAIL,
                "to": user.email,
                "subject": subject,
                "html": html_content,
                "text": text_content
            }
            
            logger.info(f"Sending email via Resend API to {user.email}")
            logger.debug(f"Email payload: {email_payload}")
            
            # Send email via Resend
            response = resend.Emails.send(email_payload)
            
            email_id = response.get('id')
            logger.info(f"Email sent successfully via Resend. Email ID: {email_id}")
            logger.info(f"Email details - To: {user.email}, Type: {email_type.value}, Subject: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {str(e)}")
            logger.error(f"Email type: {email_type.value}")
            logger.error(f"Email data: {email_data}")
            logger.error(f"Resend API error details: {traceback.format_exc()}")
            raise
    
    def _prepare_template_data(self, user: User, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare template data by combining user information with email data.
        
        Args:
            user: User object
            email_data: Additional email data
            
        Returns:
            Combined template data
        """
        logger.debug("Preparing template data for email")
        
        # Base user data
        template_data = {
            "first_name": user.first_name or "User",
            "email": user.email,
            "user_id": user.id,
        }
        
        logger.debug(f"Base user data: {template_data}")
        
        # Add common URLs
        base_url = getattr(settings, 'FRONTEND_URL', 'https://zovoice.com')
        url_data = {
            "dashboard_url": f"{base_url}/dashboard",
            "billing_url": f"{base_url}/billing",
            "support_url": f"{base_url}/support",
        }
        template_data.update(url_data)
        
        logger.debug(f"Added URL data: {url_data}")
        
        # Add email-specific data
        template_data.update(email_data)
        
        logger.debug(f"Final template data: {template_data}")
        
        return template_data

def create_email_worker() -> EmailWorker:
    """Create and return an email worker instance"""
    logger.info("Creating EmailWorker instance")
    return EmailWorker()

def run_email_worker():
    """Run the email worker"""
    logger.info("=" * 50)
    logger.info("Starting Email Worker Service")
    logger.info("=" * 50)
    
    worker = create_email_worker()
    
    try:
        logger.info("Email Worker service started successfully")
        logger.info(f"Listening on queue: email_queue")
        logger.info(f"Max retries: {worker.max_retries}")
        logger.info(f"Resend API configured: {'Yes' if hasattr(settings, 'RESEND_API_KEY') and settings.RESEND_API_KEY else 'No'}")
        logger.info(f"From email: {settings.EMAILS_FROM_EMAIL}")
        logger.info(f"Frontend URL: {settings.FRONTEND_URL}")
        logger.info("-" * 50)
        
        worker.start()
        
    except KeyboardInterrupt:
        logger.info("Email Worker stopped by user (SIGINT)")
    except Exception as e:
        logger.error(f"Email Worker failed with error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise
    finally:
        logger.info("Email Worker service shutting down")
        try:
            worker.close()
            logger.info("Email Worker connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing worker connections: {str(e)}")

if __name__ == "__main__":
    run_email_worker() 