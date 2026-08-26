"""Gmail Email Sender & MIME Message Builder."""
import base64
import html
import logging
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from services.email.gmail_auth import GmailOAuthManager
from config.settings import get_settings

logger = logging.getLogger(__name__)


class GmailSenderService:
    """Constructs and sends personalized pitch emails via Gmail API."""

    def __init__(self, auth_manager: Optional[GmailOAuthManager] = None):
        self.auth_mgr = auth_manager or GmailOAuthManager()
        self.settings = get_settings()

    def build_message(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        tracking_token: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> MIMEMultipart:
        """Create MIME multipart email message with tracking pixel."""
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["subject"] = subject

        # Plain text version
        part_text = MIMEText(body_text, "plain")
        message.attach(part_text)

        # HTML version with 1x1 tracking pixel
        # Treat AI/user-provided copy as text. Without escaping, a crafted pitch
        # could inject arbitrary HTML into the outgoing email.
        html_body = html.escape(body_text).replace("\n", "<br>")
        if tracking_token:
            pixel_url = f"{self.settings.TRACKING_BASE_URL}/open/{tracking_token}"
            tracking_html = f'<br><br><img src="{pixel_url}" width="1" height="1" style="display:none !important;" alt="" />'
            html_body += tracking_html

        part_html = MIMEText(f"<html><body>{html_body}</body></html>", "html")
        message.attach(part_html)

        return message

    def send_pitch(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        user_id: str = "default_user",
        tracking_token: Optional[str] = None,
        thread_id: Optional[str] = None,
        allow_simulation: bool = True,
    ) -> Dict[str, Any]:
        """Send email via Gmail API or simulate in mock mode."""
        creds = self.auth_mgr.get_credentials(user_id)

        mime_msg = self.build_message(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            tracking_token=tracking_token,
            thread_id=thread_id,
        )
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

        if creds:
            try:
                service = build("gmail", "v1", credentials=creds)
                body = {"raw": raw}
                if thread_id:
                    body["threadId"] = thread_id

                sent_msg = service.users().messages().send(userId="me", body=body).execute()
                logger.info("Email successfully sent via Gmail API: %s", sent_msg.get("id"))
                return {
                    "success": True,
                    "gmail_message_id": sent_msg.get("id"),
                    "gmail_thread_id": sent_msg.get("threadId"),
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "simulated": False,
                }
            except Exception as e:
                logger.error("Gmail API sending error: %s", e)
                return {
                    "success": False,
                    "error": str(e),
                    "simulated": False,
                }

        if not allow_simulation:
            return {
                "success": False,
                "error": f"Gmail sender account '{user_id}' is not connected or its authorization has expired",
                "simulated": False,
            }

        # Explicit local/test simulation mode only.
        simulated_id = f"sim_{uuid.uuid4().hex[:12]}"
        logger.info("[Simulated Mode] Email to %s would be sent: '%s'", to_email, subject)
        return {
            "success": True,
            "gmail_message_id": simulated_id,
            "gmail_thread_id": simulated_id,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }
