"""Unit tests for OpenClaw PR Core & Scoring Algorithm."""
import pytest
from core.scoring import OpenClaw4DScorer, calculate_4d_score
from core.matching import JournalistMatcher
from db.repositories.journalists_repo import JournalistsRepository


def test_4d_category_match():
    # Exact and partial beat matches
    journalist_beats = ["AI", "Machine Learning", "Tech"]
    target_beats = ["AI", "Startups"]
    score = OpenClaw4DScorer.calculate_category_match(journalist_beats, target_beats)
    assert 0.6 <= score <= 1.0

    # No match
    unrelated_beats = ["Gardening", "Cooking"]
    no_match_score = OpenClaw4DScorer.calculate_category_match(unrelated_beats, target_beats)
    assert no_match_score < 0.5


def test_4d_influence_score():
    tier1_score = OpenClaw4DScorer.estimate_influence_score("TechCrunch", "@techcrunch")
    assert tier1_score >= 0.90

    unlisted_score = OpenClaw4DScorer.estimate_influence_score("Random Local Blog")
    assert unlisted_score == 0.50


def test_4d_composite_calculation():
    scores = calculate_4d_score({
        "beat": ["AI", "Startups"],
        "outlet": "Bloomberg",
        "response_rate": 0.5,
        "relationship_score": 0.7,
    }, target_beats=["AI"])
    
    assert "overall_score" in scores
    assert 0.0 <= scores["overall_score"] <= 1.0


def test_journalist_matcher():
    repo = JournalistsRepository()
    repo.client = None
    repo._local_store.clear()
    
    # Create sample journalists
    repo.create({
        "id": "j1",
        "name": "Tech Reporter",
        "email": "tech@example.com",
        "outlet": "TechCrunch",
        "beat": ["AI", "Startups"],
        "overall_score": 0.9,
    })
    repo.create({
        "id": "j2",
        "name": "Sports Reporter",
        "email": "sports@example.com",
        "outlet": "SportsDaily",
        "beat": ["Football"],
        "overall_score": 0.4,
    })

    matcher = JournalistMatcher(repo)
    campaign = {
        "name": "New AI Tool",
        "story": "We are launching a generative AI assistant for developers.",
        "target_beat": ["AI"],
        "target_outlets": ["TechCrunch"]
    }

    ranked = matcher.rank_journalists_for_campaign(campaign, top_k=5)
    assert len(ranked) == 2
    assert ranked[0]["id"] == "j1"
    assert ranked[0]["match_score"] > ranked[1]["match_score"]
