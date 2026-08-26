"""Unit tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"


import uuid

def test_journalists_crud():
    uid = uuid.uuid4().hex[:8]
    # Create
    payload = {
        "name": "Test Reporter",
        "email": f"test.reporter.{uid}@testmedia.com",
        "outlet": "Test Media",
        "beat": ["Tech", "AI"],
        "bio": "Covering modern tech"
    }
    res = client.post("/api/v1/journalists/", json=payload)
    assert res.status_code == 200
    created = res.json()
    assert created["name"] == "Test Reporter"
    assert "overall_score" in created

    # List
    list_res = client.get("/api/v1/journalists/")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) > 0


def test_journalist_validation_and_duplicate_email():
    invalid = client.post("/api/v1/journalists/", json={"name": "A", "email": "not-an-email"})
    assert invalid.status_code == 422

    uid = uuid.uuid4().hex[:8]
    payload = {"name": "Unique Reporter", "email": f"unique.reporter.{uid}@example.com"}
    first = client.post("/api/v1/journalists/", json=payload)
    assert first.status_code == 200
    duplicate = client.post("/api/v1/journalists/", json=payload)
    assert duplicate.status_code == 409


def test_campaigns_and_match():
    # Create campaign
    c_payload = {
        "name": "Test AI Campaign",
        "story": "Announcing a major test story on artificial intelligence breakthroughs.",
        "target_beat": ["AI", "Tech"],
        "target_outlets": ["Test Media"]
    }
    res = client.post("/api/v1/campaigns/", json=c_payload)
    assert res.status_code == 200
    camp = res.json()
    camp_id = camp["id"]

    # Match journalists
    match_res = client.post(f"/api/v1/campaigns/{camp_id}/match?top_k=5")
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert "matches" in match_data
    assert len(match_data["matches"]) > 0


def test_tracking_pixel_endpoint():
    res = client.get("/api/v1/outreach/track/open/sample-token-123")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/gif"
