"""Journalists repository with Supabase and in-memory fallback."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from db.supabase_client import get_supabase_client


class JournalistsRepository:
    """Repository for journalist operations."""

    # In-memory storage when Supabase is not connected
    _local_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.client = get_supabase_client()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new journalist record."""
        journalist_id = data.get("id") or str(uuid.uuid4())
        record = {
            "id": journalist_id,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "email_status": data.get("email_status", "unverified"),
            "email_source_url": data.get("email_source_url"),
            "email_source_note": data.get("email_source_note", ""),
            "email_verified_at": data.get("email_verified_at"),
            "email_last_checked_at": data.get("email_last_checked_at"),
            "outlet": data.get("outlet", ""),
            "beat": data.get("beat", []),
            "location": data.get("location", ""),
            "twitter": data.get("twitter", ""),
            "linkedin": data.get("linkedin", ""),
            "bio": data.get("bio", ""),
            "recent_articles": data.get("recent_articles", []),
            "last_contacted": data.get("last_contacted"),
            "response_rate": data.get("response_rate", 0.0),
            "category_match": data.get("category_match", 0.5),
            "influence_score": data.get("influence_score", 0.5),
            "history_score": data.get("history_score", 0.5),
            "relationship_score": data.get("relationship_score", 0.5),
            "overall_score": data.get("overall_score", 0.5),
            "embedding": data.get("embedding"),
            "source": data.get("source", "manual"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.client:
            try:
                res = self.client.table("journalists").insert(record).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                # Log and fallback to local
                pass

        self._local_store[journalist_id] = record
        return record

    def list_all(
        self,
        beat: Optional[str] = None,
        outlet: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List journalists with optional filters."""
        if self.client:
            try:
                query = self.client.table("journalists").select("*")
                if outlet:
                    query = query.ilike("outlet", f"%{outlet}%")
                if search:
                    query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%,outlet.ilike.%{search}%")
                query = query.order("overall_score", desc=True)
                if limit is not None:
                    query = query.range(offset, offset + limit - 1)
                res = query.execute()
                if res.data is not None:
                    # Client-side beat filter if array filter
                    items = res.data
                    if beat:
                        items = [j for j in items if beat.lower() in [b.lower() for b in (j.get("beat") or [])]]
                    return items
            except Exception:
                pass

        # Fallback local list
        items = list(self._local_store.values())
        if outlet:
            items = [j for j in items if outlet.lower() in (j.get("outlet") or "").lower()]
        if beat:
            items = [j for j in items if beat.lower() in [b.lower() for b in (j.get("beat") or [])]]
        if search:
            s = search.lower()
            items = [
                j for j in items
                if s in (j.get("name") or "").lower()
                or s in (j.get("email") or "").lower()
                or s in (j.get("outlet") or "").lower()
            ]

        items.sort(key=lambda x: x.get("overall_score", 0.0), reverse=True)
        if limit is not None:
            return items[offset : offset + limit]
        return items[offset:]

    def get_by_id(self, journalist_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a journalist by ID."""
        if self.client:
            try:
                res = self.client.table("journalists").select("*").eq("id", journalist_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return self._local_store.get(journalist_id)

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch a journalist by email address."""
        if not email or not email.strip():
            return None
        if self.client:
            try:
                res = self.client.table("journalists").select("*").eq("email", email.strip().lower()).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        for j in self._local_store.values():
            if j.get("email", "").strip().lower() == email.strip().lower():
                return j
        return None

    def update(self, journalist_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update journalist attributes."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.client:
            try:
                res = self.client.table("journalists").update(updates).eq("id", journalist_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        if journalist_id in self._local_store:
            self._local_store[journalist_id].update(updates)
            return self._local_store[journalist_id]
        return None

    def delete(self, journalist_id: str) -> bool:
        """Delete a journalist."""
        if self.client:
            try:
                self.client.table("journalists").delete().eq("id", journalist_id).execute()
                return True
            except Exception:
                pass
        if journalist_id in self._local_store:
            del self._local_store[journalist_id]
            return True
        return False

    def upsert_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk upsert journalists."""
        results = []
        for rec in records:
            existing = self.get_by_email(rec.get("email", ""))
            if existing:
                updated = self.update(existing["id"], rec)
                if updated:
                    results.append(updated)
            else:
                created = self.create(rec)
                results.append(created)
        return results

    def search_semantic(
        self,
        query_embedding: List[float],
        match_threshold: float = 0.5,
        match_count: int = 20,
        filter_beat: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Use Supabase pgvector RPC match_journalists or local cosine similarity fallback."""
        if self.client:
            try:
                payload = {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": match_count,
                    "filter_beat": filter_beat,
                }
                res = self.client.rpc("match_journalists", payload).execute()
                if res.data is not None:
                    return res.data
            except Exception:
                pass

        # Fallback local calculation
        import math

        def cosine_similarity(v1: List[float], v2: List[float]) -> float:
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        matched = []
        for j in self._local_store.values():
            emb = j.get("embedding")
            sim = cosine_similarity(query_embedding, emb) if emb else 0.5
            if sim >= match_threshold:
                if filter_beat:
                    j_beats = [b.lower() for b in (j.get("beat") or [])]
                    if not any(fb.lower() in j_beats for fb in filter_beat):
                        continue
                matched.append({**j, "similarity": round(sim, 4)})

        matched.sort(key=lambda x: (x.get("similarity", 0), x.get("overall_score", 0)), reverse=True)
        return matched[:match_count]
