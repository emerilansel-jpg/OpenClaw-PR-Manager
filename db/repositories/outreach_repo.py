"""Outreach repository for managing pitches and follow-up tracking."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from db.supabase_client import get_supabase_client


class OutreachRepository:
    """Repository for outreach email tracking and follow-ups."""

    _local_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.client = get_supabase_client()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an outreach entry."""
        outreach_id = data.get("id") or str(uuid.uuid4())
        tracking_token = data.get("tracking_token") or str(uuid.uuid4())
        record = {
            "id": outreach_id,
            "campaign_id": data.get("campaign_id"),
            "journalist_id": data.get("journalist_id"),
            "subject_line": data.get("subject_line", ""),
            "pitch_email": data.get("pitch_email", ""),
            "status": data.get("status", "pending"),
            "follow_up_sequence": data.get("follow_up_sequence", 1),
            "max_follow_ups": data.get("max_follow_ups", 4),
            "next_follow_up": data.get("next_follow_up"),
            "sent_at": data.get("sent_at"),
            "opened_at": data.get("opened_at"),
            "replied_at": data.get("replied_at"),
            "gmail_message_id": data.get("gmail_message_id"),
            "gmail_thread_id": data.get("gmail_thread_id"),
            "sender_account_key": data.get("sender_account_key"),
            "tracking_token": tracking_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.client:
            try:
                res = self.client.table("outreach").insert(record).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        self._local_store[outreach_id] = record
        return record

    def list_by_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """List all outreach rows for a specific campaign."""
        if self.client:
            try:
                res = self.client.table("outreach").select("*, journalists(name, email, outlet)").eq("campaign_id", campaign_id).execute()
                if res.data is not None:
                    return res.data
            except Exception:
                pass

        return [o for o in self._local_store.values() if o.get("campaign_id") == campaign_id]

    def get_active_for_recipient(
        self,
        campaign_id: str,
        journalist_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return an unfinished outreach for a campaign/recipient pair."""
        terminal = {"replied", "bounced", "unsubscribed", "completed_no_reply", "simulated"}
        for item in self.list_by_campaign(campaign_id):
            if item.get("journalist_id") == journalist_id and item.get("status") not in terminal:
                return item
        return None

    def list_all(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """List outreach records regardless of the active storage backend."""
        if self.client:
            try:
                res = (
                    self.client.table("outreach")
                    .select("*, journalists(name, email, outlet)")
                    .order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception:
                pass

        items = list(self._local_store.values())
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[offset : offset + limit]

    def get_by_id(self, outreach_id: str) -> Optional[Dict[str, Any]]:
        """Get outreach by ID."""
        if self.client:
            try:
                res = self.client.table("outreach").select("*, journalists(name, email, outlet)").eq("id", outreach_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return self._local_store.get(outreach_id)

    def get_by_tracking_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Find outreach record by tracking token."""
        if self.client:
            try:
                res = self.client.table("outreach").select("*").eq("tracking_token", token).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        for o in self._local_store.values():
            if o.get("tracking_token") == token:
                return o
        return None

    def update(self, outreach_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update outreach record."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.client:
            try:
                res = self.client.table("outreach").update(updates).eq("id", outreach_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        if outreach_id in self._local_store:
            self._local_store[outreach_id].update(updates)
            return self._local_store[outreach_id]
        return None

    def get_due_follow_ups(self) -> List[Dict[str, Any]]:
        """Retrieve outreach records that are due for follow-up."""
        now_str = datetime.now(timezone.utc).isoformat()
        if self.client:
            try:
                res = (
                    self.client.table("outreach")
                    .select("*, journalists(name, email, outlet)")
                    .lte("next_follow_up", now_str)
                    .not_.in_("status", ["replied", "bounced", "unsubscribed"])
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception:
                pass

        due = []
        for o in self._local_store.values():
            if o.get("status") not in ["replied", "bounced", "unsubscribed"]:
                nxt = o.get("next_follow_up")
                if nxt and nxt <= now_str:
                    due.append(o)
        return due

    def get_stats(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate outreach statistics."""
        items = list(self._local_store.values())
        if self.client:
            try:
                q = self.client.table("outreach").select("status, sent_at, opened_at, replied_at")
                if campaign_id:
                    q = q.eq("campaign_id", campaign_id)
                res = q.execute()
                if res.data is not None:
                    items = res.data
            except Exception:
                pass
        elif campaign_id:
            items = [o for o in items if o.get("campaign_id") == campaign_id]

        total = len(items)
        sent = sum(
            1 for o in items
            if o.get("status") != "simulated"
            and (o.get("sent_at") or o.get("status") in ["sent", "opened", "replied", "completed_no_reply"])
        )
        opened = sum(
            1 for o in items
            if o.get("opened_at") or o.get("status") in ["opened", "replied"]
        )
        replied = sum(1 for o in items if o.get("replied_at") or o.get("status") == "replied")
        bounced = sum(1 for o in items if o.get("status") == "bounced")

        return {
            "total": total,
            "sent": sent,
            "opened": opened,
            "replied": replied,
            "bounced": bounced,
            "open_rate": (opened / sent * 100) if sent > 0 else 0.0,
            "response_rate": (replied / sent * 100) if sent > 0 else 0.0,
        }
