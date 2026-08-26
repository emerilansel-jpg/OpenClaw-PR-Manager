"""OpenClaw 4D Scoring Algorithm for Media Relations.

4 Dimensions:
1. Category Match (40%): How closely the journalist's beat/topics align with the campaign.
2. Influence Score (25%): Domain authority, tier of media outlet, social following.
3. History Score (20%): Historical response rate, coverage frequency, open rates.
4. Relationship Score (15%): Prior interactions, sentiment, exclusive embargo history.
"""
from typing import List, Dict, Any, Optional

# Media Outlet Tier Reference for influence scoring (0.0 to 1.0)
OUTLET_TIER_SCORES: Dict[str, float] = {
    # Tier 1 Global (0.95 - 1.0)
    "techcrunch": 0.98,
    "bloomberg": 0.98,
    "reuters": 0.98,
    "the wall street journal": 0.97,
    "wsj": 0.97,
    "the verge": 0.95,
    "wired": 0.95,
    "forbes": 0.94,
    "cnbc": 0.94,
    "financial times": 0.95,
    "ft": 0.95,
    
    # Tier 1 Regional / Tech (0.85 - 0.92)
    "tech in asia": 0.90,
    "venturebeat": 0.90,
    "zdnet": 0.88,
    "ars technica": 0.88,
    "the next web": 0.85,
    "kr asia": 0.85,
    
    # Tier 1 Indonesia (0.88 - 0.95)
    "kompas": 0.94,
    "detik": 0.94,
    "tempo": 0.92,
    "katadata": 0.90,
    "kumparan": 0.90,
    "bisnis indonesia": 0.90,
    "kontan": 0.88,
    "idntimes": 0.86,
    "dailysocial": 0.88,
}


class OpenClaw4DScorer:
    """Calculates 4D scoring for journalists based on campaign context."""

    WEIGHT_CATEGORY = 0.40
    WEIGHT_INFLUENCE = 0.25
    WEIGHT_HISTORY = 0.20
    WEIGHT_RELATIONSHIP = 0.15

    @classmethod
    def calculate_category_match(
        cls,
        journalist_beats: List[str],
        target_beats: List[str]
    ) -> float:
        """Calculates beat overlap similarity (Jaccard-like)."""
        if not target_beats:
            return 0.70  # Neutral high if no specific beat target

        if not journalist_beats:
            return 0.30

        j_set = {b.strip().lower() for b in journalist_beats if b}
        t_set = {b.strip().lower() for b in target_beats if b}

        if not j_set or not t_set:
            return 0.40

        intersection = j_set.intersection(t_set)
        if intersection:
            return min(1.0, 0.60 + (len(intersection) / len(t_set)) * 0.40)

        # Check partial substring matches
        partial_matches = 0
        for jb in j_set:
            for tb in t_set:
                if jb in tb or tb in jb:
                    partial_matches += 1
                    break

        if partial_matches > 0:
            return min(0.85, 0.50 + (partial_matches / len(t_set)) * 0.35)

        return 0.20

    @classmethod
    def estimate_influence_score(
        cls,
        outlet: Optional[str],
        twitter: Optional[str] = None,
        linkedin: Optional[str] = None
    ) -> float:
        """Calculates outlet influence tier + social credibility bonus."""
        score = 0.50  # Base default for independent or unlisted outlet

        if outlet:
            outlet_clean = outlet.strip().lower()
            for key, tier_score in OUTLET_TIER_SCORES.items():
                if key in outlet_clean:
                    score = tier_score
                    break

        # Minor boost for verified social profiles
        if twitter:
            score = min(1.0, score + 0.03)
        if linkedin:
            score = min(1.0, score + 0.02)

        return round(score, 3)

    @classmethod
    def calculate_history_score(
        cls,
        response_rate: float,
        outreach_count: int = 0,
        replied_count: int = 0
    ) -> float:
        """Calculates history score based on prior campaign response."""
        if outreach_count == 0:
            return 0.50  # Fresh contact neutral baseline

        calculated_rate = (replied_count / outreach_count) if outreach_count > 0 else response_rate
        # Non-linear boost: A journalist who replied before is gold in PR
        if calculated_rate > 0.30:
            return min(1.0, 0.70 + calculated_rate * 0.30)
        elif calculated_rate > 0.0:
            return 0.60 + calculated_rate * 0.30
        else:
            # Contacted multiple times without response degrades score gradually
            penalty = min(0.30, outreach_count * 0.05)
            return max(0.20, 0.50 - penalty)

    @classmethod
    def calculate_relationship_score(
        cls,
        has_met: bool = False,
        is_vip: bool = False,
        sentiment_score: float = 0.50
    ) -> float:
        """Calculates relationship closeness."""
        score = 0.50
        if is_vip:
            score += 0.30
        if has_met:
            score += 0.15
        score += (sentiment_score - 0.50) * 0.20
        return max(0.1, min(1.0, round(score, 3)))

    @classmethod
    def compute_4d_composite(
        cls,
        category_match: float,
        influence_score: float,
        history_score: float,
        relationship_score: float
    ) -> Dict[str, float]:
        """Calculates weighted overall score."""
        overall = (
            cls.WEIGHT_CATEGORY * category_match
            + cls.WEIGHT_INFLUENCE * influence_score
            + cls.WEIGHT_HISTORY * history_score
            + cls.WEIGHT_RELATIONSHIP * relationship_score
        )
        return {
            "category_match": round(category_match, 3),
            "influence_score": round(influence_score, 3),
            "history_score": round(history_score, 3),
            "relationship_score": round(relationship_score, 3),
            "overall_score": round(overall, 3),
        }


def calculate_4d_score(
    journalist_data: Dict[str, Any],
    target_beats: Optional[List[str]] = None
) -> Dict[str, float]:
    """Convenience helper function."""
    cat = OpenClaw4DScorer.calculate_category_match(
        journalist_data.get("beat") or [],
        target_beats or []
    )
    inf = journalist_data.get("influence_score") or OpenClaw4DScorer.estimate_influence_score(
        journalist_data.get("outlet"),
        journalist_data.get("twitter"),
        journalist_data.get("linkedin")
    )
    hist = journalist_data.get("history_score") or OpenClaw4DScorer.calculate_history_score(
        journalist_data.get("response_rate", 0.0)
    )
    rel = journalist_data.get("relationship_score", 0.50)

    return OpenClaw4DScorer.compute_4d_composite(cat, inf, hist, rel)
