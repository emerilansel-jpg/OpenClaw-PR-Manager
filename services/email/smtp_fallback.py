"""
SMTP Fallback Email Sender
Provides backup email delivery when Gmail API is unavailable
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SMTPFallbackSender:
    """
    Backup email sender using standard SMTP protocol.
    
    Used as fallback when Gmail API is unavailable or fails.
    Supports TLS/SSL encryption for secure transmission.
    """
    
    def __init__(
        self,
        host: str = "smtp.gmail.com",
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        Initialize SMTP connection.
        
        Args:
            host: SMTP server hostname
            port: SMTP server port (587 for TLS, 465 for SSL)
            username: Sender email address
            password: Sender password/app password
            use_tls: Whether to use TLS encryption
        """
        
        self.host = host
        self.port = port
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.use_tls = use_tls
        
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured - fallback will not work")
    
    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_name: str = "OpenClaw PR Manager"
    ) -> dict:
        """
        Send email via SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject line
            body_html: HTML version of email body
            body_text: Plain text version (optional, auto-generated if not provided)
            from_name: Sender display name
            
        Returns:
            Dictionary with send status and details
        """
        
        if not self.username or not self.password:
            logger.error("Cannot send email - SMTP credentials missing")
            return {
                "sent": False,
                "error": "SMTP not configured",
                "fallback_used": True
            }
        
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{self.username}>"
            msg['To'] = to
            
            # Generate plain text version if not provided
            if body_text is None:
                # Simple HTML to text conversion
                import re
                body_text = re.sub('<[^<]+?>', '', body_html)
                body_text = body_text.replace('&nbsp;', ' ')
                body_text = re.sub(r'\s+', ' ', body_text).strip()
            
            # Attach both versions
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Create SMTP session with encryption
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                
                # Login
                server.login(self.username, self.password)
                
                # Send email
                server.sendmail(self.username, to, msg.as_string())
                
                logger.info(f"✅ SMTP email sent to {to}")
                
                return {
                    "sent": True,
                    "message": "Email delivered via SMTP",
                    "service": "smtp",
                    "fallback_used": True
                }
                
        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP authentication failed - check username/password"
            logger.error(error_msg)
            return {
                "sent": False,
                "error": error_msg,
                "fallback_used": True
            }
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return {
                "sent": False,
                "error": error_msg,
                "fallback_used": True
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {
                "sent": False,
                "error": error_msg,
                "fallback_used": True
            }
    
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        
        return bool(self.username and self.password)


# Global SMTP fallback instance
smtp_fallback = SMTPFallbackSender()
