from typing import Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

class EmailType(Enum):
    """Enumeration of all supported email types"""
    WELCOME = "welcome"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    BOOK_PROCESSING_COMPLETE = "book_processing_complete"
    BOOK_PROCESSING_FAILED = "book_processing_failed"
    AUDIO_GENERATION_COMPLETE = "audio_generation_complete"
    AUDIO_GENERATION_FAILED = "audio_generation_failed"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    CREDIT_LOW = "credit_low"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_ACTIVATED = "account_activated"

@dataclass
class EmailTemplate:
    """Email template configuration"""
    subject: str
    html_template: str
    text_template: str

class EmailTemplateManager:
    """Manages email templates and provides methods to render them"""
    
    def __init__(self):
        self._templates: Dict[EmailType, EmailTemplate] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register all default email templates"""
        
        # Welcome email
        self._templates[EmailType.WELCOME] = EmailTemplate(
            subject="Welcome to Jasper Voice! 🎉",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome to Jasper Voice</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to Jasper Voice! 🎉</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Welcome to Jasper Voice - your AI-powered voice generation platform!</p>
                        <p>We're excited to have you on board. Here's what you can do with Jasper Voice:</p>
                        <ul>
                            <li>🎙️ Create custom AI voices from your own recordings</li>
                            <li>📚 Convert books and documents to audio</li>
                            <li>🎵 Generate high-quality voice content</li>
                            <li>⚡ Process large files efficiently</li>
                        </ul>
                        <p>You've been credited with <strong>{credits} credits</strong> to get started!</p>
                        <a href="{dashboard_url}" class="button">Go to Dashboard</a>
                        <p>If you have any questions, feel free to reach out to our support team.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Welcome to Jasper Voice! 🎉

            Hi {first_name}!

            Welcome to Jasper Voice - your AI-powered voice generation platform!

            We're excited to have you on board. Here's what you can do with Jasper Voice:

            🎙️ Create custom AI voices from your own recordings
            📚 Convert books and documents to audio
            🎵 Generate high-quality voice content
            ⚡ Process large files efficiently

            You've been credited with {credits} credits to get started!

            Go to Dashboard: {dashboard_url}

            If you have any questions, feel free to reach out to our support team.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Email verification
        self._templates[EmailType.EMAIL_VERIFICATION] = EmailTemplate(
            subject="Verify Your Email Address",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verify Your Email</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #667eea; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .verification-code { background: #e8f4fd; border: 2px solid #667eea; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0; font-size: 24px; font-weight: bold; color: #667eea; }
                    .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Verify Your Email Address</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Thanks for signing up for Jasper Voice! To complete your registration, please verify your email address.</p>
                        <p>Your verification code is:</p>
                        <div class="verification-code">{verification_code}</div>
                        <p>This code will expire in 10 minutes.</p>
                        <p>If you didn't create an account with Jasper Voice, you can safely ignore this email.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Verify Your Email Address

            Hi {first_name}!

            Thanks for signing up for Jasper Voice! To complete your registration, please verify your email address.

            Your verification code is: {verification_code}

            This code will expire in 10 minutes.

            If you didn't create an account with Jasper Voice, you can safely ignore this email.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Password reset
        self._templates[EmailType.PASSWORD_RESET] = EmailTemplate(
            subject="Reset Your Password",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reset Your Password</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Reset Your Password</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>We received a request to reset your password for your Jasper Voice account.</p>
                        <p>Click the button below to reset your password:</p>
                        <a href="{reset_url}" class="button">Reset Password</a>
                        <p>This link will expire in 1 hour.</p>
                        <p>If you didn't request a password reset, you can safely ignore this email.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Reset Your Password

            Hi {first_name}!

            We received a request to reset your password for your Jasper Voice account.

            Click the link below to reset your password:
            {reset_url}

            This link will expire in 1 hour.

            If you didn't request a password reset, you can safely ignore this email.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Book processing complete
        self._templates[EmailType.BOOK_PROCESSING_COMPLETE] = EmailTemplate(
            subject="Your Book Processing is Complete! 📚",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Book Processing Complete</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #28a745; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Your Book Processing is Complete! 📚</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Great news! Your book "<strong>{book_title}</strong>" has been successfully processed and is ready for voice generation.</p>
                        <p>Processing details:</p>
                        <ul>
                            <li>📖 Total pages processed: {total_pages}</li>
                            <li>📝 Total words extracted: {total_words}</li>
                            <li>⏱️ Processing time: {processing_time}</li>
                        </ul>
                        <a href="{project_url}" class="button">View Project</a>
                        <p>You can now proceed to generate audio for your book using your preferred voice settings.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Your Book Processing is Complete! 📚

            Hi {first_name}!

            Great news! Your book "{book_title}" has been successfully processed and is ready for voice generation.

            Processing details:
            📖 Total pages processed: {total_pages}
            📝 Total words extracted: {total_words}
            ⏱️ Processing time: {processing_time}

            View Project: {project_url}

            You can now proceed to generate audio for your book using your preferred voice settings.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Book processing failed
        self._templates[EmailType.BOOK_PROCESSING_FAILED] = EmailTemplate(
            subject="Book Processing Failed ❌",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Book Processing Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Book Processing Failed ❌</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>We're sorry, but the processing of your book "<strong>{book_title}</strong>" has failed.</p>
                        <p>Error details: {error_message}</p>
                        <p>Possible solutions:</p>
                        <ul>
                            <li>Check if the file format is supported (PDF, EPUB)</li>
                            <li>Ensure the file is not corrupted</li>
                            <li>Try uploading a smaller file</li>
                            <li>Contact support if the issue persists</li>
                        </ul>
                        <a href="{project_url}" class="button">View Project</a>
                        <p>If you continue to experience issues, please contact our support team.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Book Processing Failed ❌

            Hi {first_name}!

            We're sorry, but the processing of your book "{book_title}" has failed.

            Error details: {error_message}

            Possible solutions:
            - Check if the file format is supported (PDF, EPUB)
            - Ensure the file is not corrupted
            - Try uploading a smaller file
            - Contact support if the issue persists

            View Project: {project_url}

            If you continue to experience issues, please contact our support team.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Audio generation complete
        self._templates[EmailType.AUDIO_GENERATION_COMPLETE] = EmailTemplate(
            subject="Your Audio Generation is Complete! 🎵",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Audio Generation Complete</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #17a2b8; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #17a2b8; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Your Audio Generation is Complete! 🎵</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Excellent! Your audio generation for "<strong>{project_title}</strong>" has been completed successfully.</p>
                        <p>Generation details:</p>
                        <ul>
                            <li>🎙️ Voice used: {voice_name}</li>
                            <li>⏱️ Duration: {audio_duration}</li>
                            <li>📁 File size: {file_size}</li>
                            <li>💾 Credits used: {credits_used}</li>
                        </ul>
                        <a href="{project_url}" class="button">Download Audio</a>
                        <p>Your audio file is ready for download. Enjoy listening to your generated content!</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Your Audio Generation is Complete! 🎵

            Hi {first_name}!

            Excellent! Your audio generation for "{project_title}" has been completed successfully.

            Generation details:
            🎙️ Voice used: {voice_name}
            ⏱️ Duration: {audio_duration}
            📁 File size: {file_size}
            💾 Credits used: {credits_used}

            Download Audio: {project_url}

            Your audio file is ready for download. Enjoy listening to your generated content!

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Audio generation failed
        self._templates[EmailType.AUDIO_GENERATION_FAILED] = EmailTemplate(
            subject="Audio Generation Failed ❌",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Audio Generation Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Audio Generation Failed ❌</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>We're sorry, but the audio generation for "<strong>{project_title}</strong>" has failed.</p>
                        <p>Error details: {error_message}</p>
                        <p>Your credits have been refunded to your account.</p>
                        <a href="{project_url}" class="button">View Project</a>
                        <p>If you continue to experience issues, please contact our support team.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Audio Generation Failed ❌

            Hi {first_name}!

            We're sorry, but the audio generation for "{project_title}" has failed.

            Error details: {error_message}

            Your credits have been refunded to your account.

            View Project: {project_url}

            If you continue to experience issues, please contact our support team.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Payment success
        self._templates[EmailType.PAYMENT_SUCCESS] = EmailTemplate(
            subject="Payment Successful! 💳",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Successful</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #28a745; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Payment Successful! 💳</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Thank you for your purchase! Your payment has been processed successfully.</p>
                        <p>Payment details:</p>
                        <ul>
                            <li>💰 Amount: ${amount}</li>
                            <li>💳 Credits purchased: {credits}</li>
                            <li>📅 Date: {payment_date}</li>
                            <li>🆔 Transaction ID: {transaction_id}</li>
                        </ul>
                        <a href="{dashboard_url}" class="button">Go to Dashboard</a>
                        <p>Your credits have been added to your account and are ready to use!</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Payment Successful! 💳

            Hi {first_name}!

            Thank you for your purchase! Your payment has been processed successfully.

            Payment details:
            💰 Amount: ${amount}
            💳 Credits purchased: {credits}
            📅 Date: {payment_date}
            🆔 Transaction ID: {transaction_id}

            Go to Dashboard: {dashboard_url}

            Your credits have been added to your account and are ready to use!

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Payment failed
        self._templates[EmailType.PAYMENT_FAILED] = EmailTemplate(
            subject="Payment Failed ❌",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Payment Failed ❌</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>We're sorry, but your payment has failed.</p>
                        <p>Payment details:</p>
                        <ul>
                            <li>💰 Amount: ${amount}</li>
                            <li>💳 Credits: {credits}</li>
                            <li>📅 Date: {payment_date}</li>
                            <li>❌ Error: {error_message}</li>
                        </ul>
                        <a href="{billing_url}" class="button">Try Again</a>
                        <p>Please check your payment method and try again. If the issue persists, contact our support team.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Payment Failed ❌

            Hi {first_name}!

            We're sorry, but your payment has failed.

            Payment details:
            💰 Amount: ${amount}
            💳 Credits: {credits}
            📅 Date: {payment_date}
            ❌ Error: {error_message}

            Try Again: {billing_url}

            Please check your payment method and try again. If the issue persists, contact our support team.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Credit low
        self._templates[EmailType.CREDIT_LOW] = EmailTemplate(
            subject="Low Credits Alert ⚠️",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Low Credits Alert</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #ffc107; color: #333; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #ffc107; color: #333; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Low Credits Alert ⚠️</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Your Jasper Voice account is running low on credits.</p>
                        <p>Current balance: <strong>{current_credits} credits</strong></p>
                        <p>To continue generating audio content, please purchase more credits.</p>
                        <a href="{billing_url}" class="button">Buy Credits</a>
                        <p>Don't let your creative process be interrupted!</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Low Credits Alert ⚠️

            Hi {first_name}!

            Your Jasper Voice account is running low on credits.

            Current balance: {current_credits} credits

            To continue generating audio content, please purchase more credits.

            Buy Credits: {billing_url}

            Don't let your creative process be interrupted!

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Account suspended
        self._templates[EmailType.ACCOUNT_SUSPENDED] = EmailTemplate(
            subject="Account Suspended ⚠️",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Account Suspended</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Account Suspended ⚠️</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Your Jasper Voice account has been suspended due to: <strong>{suspension_reason}</strong></p>
                        <p>To reactivate your account, please contact our support team.</p>
                        <a href="{support_url}" class="button">Contact Support</a>
                        <p>We're here to help resolve any issues and get you back to creating amazing audio content.</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Account Suspended ⚠️

            Hi {first_name}!

            Your Jasper Voice account has been suspended due to: {suspension_reason}

            To reactivate your account, please contact our support team.

            Contact Support: {support_url}

            We're here to help resolve any issues and get you back to creating amazing audio content.

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
        
        # Account activated
        self._templates[EmailType.ACCOUNT_ACTIVATED] = EmailTemplate(
            subject="Account Reactivated! ✅",
            html_template="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Account Reactivated</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #28a745; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                    .button { display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Account Reactivated! ✅</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {first_name}!</h2>
                        <p>Great news! Your Jasper Voice account has been reactivated successfully.</p>
                        <p>You can now continue using all our services and features.</p>
                        <a href="{dashboard_url}" class="button">Go to Dashboard</a>
                        <p>Thank you for your patience. We're excited to have you back!</p>
                        <p>Best regards,<br>The Jasper Voice Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 Jasper Voice. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text_template="""
            Account Reactivated! ✅

            Hi {first_name}!

            Great news! Your Jasper Voice account has been reactivated successfully.

            You can now continue using all our services and features.

            Go to Dashboard: {dashboard_url}

            Thank you for your patience. We're excited to have you back!

            Best regards,
            The Jasper Voice Team

            © 2024 Jasper Voice. All rights reserved.
            """
        )
    
    def get_template(self, email_type: EmailType) -> EmailTemplate:
        """Get an email template by type"""
        if email_type not in self._templates:
            raise ValueError(f"Email template not found for type: {email_type}")
        return self._templates[email_type]
    
    def render_template(self, email_type: EmailType, data: Dict[str, Any]) -> tuple[str, str]:
        """
        Render an email template with the provided data
        
        Returns:
            tuple: (html_content, text_content)
        """
        template = self.get_template(email_type)
        
        # Render HTML template
        html_content = template.html_template.format(**data)
        
        # Render text template
        text_content = template.text_template.format(**data)
        
        return html_content, text_content
    
    def add_template(self, email_type: EmailType, template: EmailTemplate):
        """Add a new email template"""
        self._templates[email_type] = template
    
    def list_templates(self) -> list[EmailType]:
        """List all available email template types"""
        return list(self._templates.keys())

# Global instance
template_manager = EmailTemplateManager() 