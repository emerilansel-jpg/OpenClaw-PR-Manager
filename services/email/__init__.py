"""Email package."""
from services.email.gmail_auth import GmailOAuthManager
from services.email.sender import GmailSenderService
from services.email.tracker import EmailTrackerService

__all__ = [
    "GmailOAuthManager",
    "GmailSenderService",
    "EmailTrackerService",
]
