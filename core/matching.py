"""Journalist-to-Campaign matching engine combining AI semantic search and OpenClaw 4D scoring."""
from typing import List, Dict, Any, Optional
from core.scoring import calculate_4d_score
from db.repositories.journalists_repo import JournalistsRepository


class JournalistMatcher:
    """Matches journalists to a campaign's press release story."""

    SEMANTIC_WEIGHT = 0.55
    SCORE_4D_WEIGHT = 0.45

    def __init__(self, journalists_repo: Optional[JournalistsRepository] = None):
        self.repo = journalists_repo or JournalistsRepository()

    def rank_journalists_for_campaign(
        self,
        campaign: Dict[str, Any],
        query_embedding: Optional[List[float]] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Rank journalists combining semantic similarity and OpenClaw 4D scoring."""
        target_beats = campaign.get("target_beat") or []
        target_outlets = [o.lower() for o in (campaign.get("target_outlets") or []) if o]

        # 1. Fetch candidate pool
        candidates = []
        if query_embedding:
            candidates = self.repo.search_semantic(
                query_embedding=query_embedding,
                match_threshold=0.0,
                match_count=top_k * 2,
                filter_beat=None,
            )
        
        if not candidates:
            candidates = self.repo.list_all(limit=top_k * 3)

        results = []
        for cand in candidates:
            # Recompute 4D score based on this specific campaign's target beats
            score_dict = calculate_4d_score(cand, target_beats=target_beats)
            
            # Semantic similarity factor
            sem_sim = cand.get("similarity", 0.60)
            
            # Target outlet bonus
            outlet = (cand.get("outlet") or "").lower()
            outlet_bonus = 0.15 if any(to in outlet for to in target_outlets) else 0.0

            # Composite final ranking match score
            match_score = (
                self.SEMANTIC_WEIGHT * sem_sim
                + self.SCORE_4D_WEIGHT * score_dict["overall_score"]
                + outlet_bonus
            )
            match_score = min(1.0, round(match_score, 3))

            results.append({
                **cand,
                "calculated_4d": score_dict,
                "semantic_similarity": round(sem_sim, 3),
                "match_score": match_score,
                "match_percentage": int(match_score * 100),
            })

        # Sort by final match score descending
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:top_k]
