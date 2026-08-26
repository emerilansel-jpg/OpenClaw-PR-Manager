"""Automatic Gmail Reply Detection Service."""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build

from db.repositories.outreach_repo import OutreachRepository
from db.repositories.journalists_repo import JournalistsRepository
from services.email.gmail_auth import GmailOAuthManager
from services.email.tracker import EmailTrackerService

logger = logging.getLogger(__name__)


class GmailReplySyncService:
    """Polls Gmail threads to automatically detect incoming responses from journalists."""

    def __init__(
        self,
        outreach_repo: Optional[OutreachRepository] = None,
        journalists_repo: Optional[JournalistsRepository] = None,
        auth_manager: Optional[GmailOAuthManager] = None,
        tracker_service: Optional[EmailTrackerService] = None,
    ):
        self.outreach_repo = outreach_repo or OutreachRepository()
        self.journalists_repo = journalists_repo or JournalistsRepository()
        self.auth_mgr = auth_manager or GmailOAuthManager()
        self.tracker = tracker_service or EmailTrackerService(self.outreach_repo, self.journalists_repo)

    def sync_replies(self) -> Dict[str, Any]:
        """Check all active outreach threads in Gmail for incoming journalist replies."""
        # 1. Fetch active outreach records
        all_outreach = self.outreach_repo.list_all()
        active_candidates = [
            o for o in all_outreach
            if o.get("status") in ["sent", "opened"]
            and o.get("gmail_thread_id")
            and not o.get("gmail_message_id", "").startswith("sim_")
        ]

        checked_count = 0
        detected_replies = []

        for outreach in active_candidates:
            thread_id = outreach.get("gmail_thread_id")
            sender_key = outreach.get("sender_account_key") or "default_user"
            journalist_id = outreach.get("journalist_id")
            
            journalist = self.journalists_repo.get_by_id(journalist_id) if journalist_id else None
            journalist_email = (journalist.get("email") or "").strip().lower() if journalist else ""

            creds = self.auth_mgr.get_credentials(sender_key)
            if not creds:
                continue

            try:
                service = build("gmail", "v1", credentials=creds, cache_discovery=False)
                thread_data = service.users().threads().get(userId="me", id=thread_id).execute()
                messages = thread_data.get("messages", [])
                checked_count += 1

                # If thread has more than 1 message, inspect the later messages
                if len(messages) > 1:
                    for msg in messages[1:]:
                        headers = msg.get("payload", {}).get("headers", [])
                        from_header = next((h["value"] for h in headers if h.get("name", "").lower() == "from"), "").lower()

                        # Check if message is from the journalist or does not match sender
                        is_from_journalist = journalist_email and (journalist_email in from_header)
                        is_not_from_sender = sender_key.lower() not in from_header

                        if is_from_journalist or is_not_from_sender:
                            # Recorded reply found!
                            self.tracker.record_reply(outreach["id"])
                            detected_replies.append({
                                "outreach_id": outreach["id"],
                                "journalist": journalist.get("name") if journalist else "Unknown",
                                "journalist_email": journalist_email,
                                "sender_account": sender_key,
                                "from_header": from_header,
                                "snippet": msg.get("snippet", "")[:100],
                            })
                            logger.info(
                                "Auto-detected reply for outreach %s from %s",
                                outreach["id"],
                                from_header,
                            )
                            break
            except Exception as exc:
                logger.warning("Failed to check Gmail thread %s for replies: %s", thread_id, exc)

        return {
            "checked_threads": checked_count,
            "replies_detected": len(detected_replies),
            "details": detected_replies,
        }
