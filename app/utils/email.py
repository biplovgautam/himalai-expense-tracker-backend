import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from ..core.logging import logger

load_dotenv()

# Get email configuration from environment variables
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@himalai.com")

async def send_verification_email(to_email: str, verification_code: str):
    """
    Send verification email with the verification code.
    """
    # Simple implementation - for a real app, you'd want to use a service like SendGrid
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = EMAIL_FROM
        message["To"] = to_email
        message["Subject"] = "Verify Your Himalai Account"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Welcome to Himalai Expense Analysis!</h2>
            <p>Thank you for signing up. To verify your email address, please use the following code:</p>
            <h3 style="background-color: #f2f2f2; padding: 10px; font-family: monospace;">{verification_code}</h3>
            <p>This code will expire in 24 hours.</p>
            <p>If you didn't sign up for Himalai, please ignore this email.</p>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        # Connect to server and send email
        if EMAIL_USERNAME and EMAIL_PASSWORD:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(message)
                logger.info(f"Verification email sent to {to_email}")
        else:
            logger.warning("Email credentials not configured. Verification email not sent.")
            logger.debug(f"Would have sent verification code {verification_code} to {to_email}")
    
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        # In a production app, you might want to use a more robust email service
        # that provides better error handling and delivery guarantees