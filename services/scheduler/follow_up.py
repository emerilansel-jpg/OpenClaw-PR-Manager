"""Follow-up Automation Engine (3+7+7+14 Days Sequence)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.journalists_repo import JournalistsRepository
from services.ai.orchestrator import AIPitchOrchestrator
from services.email.sender import GmailSenderService

logger = logging.getLogger(__name__)

# Days offset for each sequence stage
FOLLOW_UP_INTERVALS = {
    1: 3,   # Initial -> F1: 3 days
    2: 7,   # F1 -> F2: 7 days (Day 10 total)
    3: 7,   # F2 -> F3: 7 days (Day 17 total)
    4: 14,  # F3 -> Breakup: 14 days (Day 31 total)
}

TERMINAL_STATUSES = {"replied", "bounced", "unsubscribed", "completed_no_reply", "simulated"}
DELIVERED_STATUSES = {"sent", "opened", *TERMINAL_STATUSES}


class FollowUpScheduler:
    """State machine and executor for the 3+7+7+14 follow-up formula."""

    def __init__(
        self,
        outreach_repo: Optional[OutreachRepository] = None,
        campaigns_repo: Optional[CampaignsRepository] = None,
        journalists_repo: Optional[JournalistsRepository] = None,
        ai_orchestrator: Optional[AIPitchOrchestrator] = None,
        email_sender: Optional[GmailSenderService] = None,
    ):
        self.outreach_repo = outreach_repo or OutreachRepository()
        self.campaigns_repo = campaigns_repo or CampaignsRepository()
        self.journalists_repo = journalists_repo or JournalistsRepository()
        self.ai = ai_orchestrator or AIPitchOrchestrator()
        self.sender = email_sender or GmailSenderService()

    @staticmethod
    def calculate_next_follow_up(current_sequence: int, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculates next follow up datetime based on 3+7+7+14 formula."""
        if current_sequence not in FOLLOW_UP_INTERVALS:
            return None  # Sequence completed
        days = FOLLOW_UP_INTERVALS[current_sequence]
        start = base_time or datetime.now(timezone.utc)
        return start + timedelta(days=days)

    def dispatch_initial_pitch(
        self,
        outreach_id: str,
        user_id: str = "default_user",
        allow_simulation: bool = True,
    ) -> Dict[str, Any]:
        """Send the initial pitch and set next follow-up to +3 days."""
        outreach = self.outreach_repo.get_by_id(outreach_id)
        if not outreach:
            return {"success": False, "error": "Outreach record not found"}

        if outreach.get("status") in DELIVERED_STATUSES:
            return {
                "success": True,
                "already_sent": True,
                "outreach_id": outreach_id,
                "next_follow_up": outreach.get("next_follow_up"),
                "simulated": str(outreach.get("gmail_message_id", "")).startswith("sim_"),
            }

        if not str(outreach.get("subject_line") or "").strip():
            return {"success": False, "error": "Subject line is required"}
        if not str(outreach.get("pitch_email") or "").strip():
            return {"success": False, "error": "Pitch email body is required"}

        journalist_id = outreach.get("journalist_id")
        journalist = self.journalists_repo.get_by_id(journalist_id)
        if not journalist or not journalist.get("email"):
            return {"success": False, "error": "Journalist email missing"}

        sender_account_key = outreach.get("sender_account_key") or user_id

        # Send email
        send_res = self.sender.send_pitch(
            to_email=journalist["email"],
            subject=outreach["subject_line"],
            body_text=outreach["pitch_email"],
            user_id=sender_account_key,
            tracking_token=outreach.get("tracking_token"),
            allow_simulation=allow_simulation,
        )

        if send_res.get("success"):
            simulated = bool(send_res.get("simulated"))
            next_date = None if simulated else self.calculate_next_follow_up(1)
            self.outreach_repo.update(outreach_id, {
                "status": "simulated" if simulated else "sent",
                "follow_up_sequence": 1,
                "sent_at": send_res.get("sent_at"),
                "gmail_message_id": send_res.get("gmail_message_id"),
                "gmail_thread_id": send_res.get("gmail_thread_id"),
                "sender_account_key": None if simulated else sender_account_key,
                "next_follow_up": next_date.isoformat() if next_date else None,
            })
            return {
                "success": True,
                "already_sent": False,
                "outreach_id": outreach_id,
                "next_follow_up": next_date,
                "simulated": simulated,
            }
        return {"success": False, "error": send_res.get("error", "Sending failed")}

    def process_due_follow_ups(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """Processes all pending follow-ups that have reached their scheduled time."""
        due_items = self.outreach_repo.get_due_follow_ups()
        processed = []

        for candidate in due_items:
            try:
                # Re-read immediately before sending. The recipient may have
                # replied or unsubscribed after the due-list query completed.
                item = self.outreach_repo.get_by_id(candidate["id"])
                if not item or item.get("status") in TERMINAL_STATUSES:
                    continue

                current_seq = int(item.get("follow_up_sequence", 1))
                next_seq = current_seq + 1

                if next_seq > 5:
                    self.outreach_repo.update(item["id"], {
                        "status": "completed_no_reply",
                        "next_follow_up": None,
                    })
                    continue

                pitch_type = {
                    2: "followup_1",
                    3: "followup_2",
                    4: "followup_3",
                    5: "breakup",
                }[next_seq]

                journalist = self.journalists_repo.get_by_id(item["journalist_id"])
                campaign = self.campaigns_repo.get_by_id(item["campaign_id"])
                if not journalist or not journalist.get("email") or not campaign:
                    continue

                followup_content = self.ai.generate_pitch(
                    journalist={**journalist, **item},
                    campaign=campaign,
                    pitch_type=pitch_type,
                )
                body = str(followup_content.get("pitch_email") or "").strip()
                if not body:
                    raise ValueError("AI generated an empty follow-up body")

                sender_account_key = item.get("sender_account_key") or user_id
                send_res = self.sender.send_pitch(
                    to_email=journalist["email"],
                    subject=f"Re: {item.get('subject_line')}",
                    body_text=body,
                    user_id=sender_account_key,
                    tracking_token=item.get("tracking_token"),
                    thread_id=item.get("gmail_thread_id"),
                    allow_simulation=False,
                )

                if not send_res.get("success"):
                    processed.append({
                        "outreach_id": item["id"],
                        "sequence": next_seq,
                        "recipient": journalist["email"],
                        "success": False,
                        "error": send_res.get("error", "Sending failed"),
                    })
                    continue

                next_date = self.calculate_next_follow_up(next_seq)
                self.outreach_repo.update(item["id"], {
                    "follow_up_sequence": next_seq,
                    "pitch_email": body,
                    "status": "completed_no_reply" if next_date is None else item.get("status", "sent"),
                    "next_follow_up": next_date.isoformat() if next_date else None,
                })
                processed.append({
                    "outreach_id": item["id"],
                    "sequence": next_seq,
                    "recipient": journalist["email"],
                    "success": True,
                    "simulated": bool(send_res.get("simulated")),
                })
            except Exception as exc:
                logger.exception("Follow-up processing failed for %s", candidate.get("id"))
                processed.append({
                    "outreach_id": candidate.get("id"),
                    "success": False,
                    "error": str(exc),
                })

        return processed
