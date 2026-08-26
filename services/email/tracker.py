"""Email Open & Reply Tracker Service."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.journalists_repo import JournalistsRepository


class EmailTrackerService:
    """Handles open pixel hits and status updates."""

    # 1x1 transparent GIF bytes
    TRANSPARENT_PIXEL_BYTES = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04"
        b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )

    def __init__(
        self,
        outreach_repo: Optional[OutreachRepository] = None,
        journalists_repo: Optional[JournalistsRepository] = None,
    ):
        self.outreach_repo = outreach_repo or OutreachRepository()
        self.journalists_repo = journalists_repo or JournalistsRepository()

    def record_open(self, tracking_token: str) -> bool:
        """Mark outreach as opened upon pixel load."""
        record = self.outreach_repo.get_by_tracking_token(tracking_token)
        if not record:
            return False

        # Preserve terminal states and the first open timestamp. A late image
        # proxy request must never revive a bounced or unsubscribed outreach.
        if record.get("status") not in (
            "opened",
            "replied",
            "bounced",
            "unsubscribed",
            "completed_no_reply",
        ):
            self.outreach_repo.update(record["id"], {
                "status": "opened",
                "opened_at": datetime.now(timezone.utc).isoformat(),
            })
        return True

    def record_reply(self, outreach_id: str) -> bool:
        """Mark outreach as replied and boost journalist history score."""
        record = self.outreach_repo.get_by_id(outreach_id)
        if not record:
            return False

        # Webhooks and manual controls may deliver the same event more than once.
        # A reply must only affect relationship scores once.
        if record.get("status") == "replied":
            return True

        self.outreach_repo.update(outreach_id, {
            "status": "replied",
            "replied_at": datetime.now(timezone.utc).isoformat(),
        })

        # Update journalist last contacted and bump relationship/history
        journalist_id = record.get("journalist_id")
        if journalist_id:
            j = self.journalists_repo.get_by_id(journalist_id)
            if j:
                current_rate = j.get("response_rate", 0.0)
                new_rate = min(1.0, current_rate + 0.20)
                self.journalists_repo.update(journalist_id, {
                    "last_contacted": datetime.now(timezone.utc).isoformat(),
                    "response_rate": new_rate,
                    "history_score": min(1.0, (j.get("history_score", 0.5) + 0.25)),
                    "relationship_score": min(1.0, (j.get("relationship_score", 0.5) + 0.20)),
                })

        return True
