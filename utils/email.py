import aiosmtplib
from email.message import EmailMessage
from core.config import settings

async def send_email_async(subject: str, recipient: str, body: str):
    message = EmailMessage()
    message["From"] = settings.EMAILS_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=True,
    ) 