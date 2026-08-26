"""Campaigns repository with Supabase and in-memory fallback."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from db.supabase_client import get_supabase_client


class CampaignsRepository:
    """Repository for managing PR campaigns."""

    _local_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.client = get_supabase_client()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign."""
        campaign_id = data.get("id") or str(uuid.uuid4())
        record = {
            "id": campaign_id,
            "name": data.get("name", "Untitled Campaign"),
            "story": data.get("story", ""),
            "story_embedding": data.get("story_embedding"),
            "target_beat": data.get("target_beat", []),
            "target_outlets": data.get("target_outlets", []),
            "status": data.get("status", "draft"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.client:
            try:
                res = self.client.table("campaigns").insert(record).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        self._local_store[campaign_id] = record
        return record

    def list_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List all campaigns."""
        if self.client:
            try:
                res = self.client.table("campaigns").select("*").order("created_at", desc=True).range(offset, offset + limit - 1).execute()
                if res.data is not None:
                    return res.data
            except Exception:
                pass

        items = list(self._local_store.values())
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[offset : offset + limit]

    def get_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get single campaign by ID."""
        if self.client:
            try:
                res = self.client.table("campaigns").select("*").eq("id", campaign_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return self._local_store.get(campaign_id)

    def update(self, campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update campaign data."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.client:
            try:
                res = self.client.table("campaigns").update(updates).eq("id", campaign_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        if campaign_id in self._local_store:
            self._local_store[campaign_id].update(updates)
            return self._local_store[campaign_id]
        return None

    def delete(self, campaign_id: str) -> bool:
        """Delete campaign."""
        if self.client:
            try:
                self.client.table("campaigns").delete().eq("id", campaign_id).execute()
                return True
            except Exception:
                pass
        if campaign_id in self._local_store:
            del self._local_store[campaign_id]
            return True
        return False
