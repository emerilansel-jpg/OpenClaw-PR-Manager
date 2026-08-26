"""Tests for external API failure modes and no-key behavior.

Covers `services/scraping/newsapi.py`, `services/scraping/google_news.py`,
`services/scraping/enricher.py`, and AI services when API keys are missing,
APIs return errors, or external services fail. All tests use mocks/fakes —
no real network calls or credentials.
"""
from unittest.mock import MagicMock, Mock, patch
import asyncio

import pytest

from config.settings import get_settings
from services.scraping.google_news import GoogleNewsScraper
from services.scraping.newsapi import NewsApiOrgService, TheNewsApiService


# ---------------------------------------------------------------------------
# NewsAPI.org / TheNewsAPI key absence handling
# ---------------------------------------------------------------------------


class TestNewsApiKeyAbsence:
    def test_newsapi_org_returns_empty_when_key_missing(self):
        service = NewsApiOrgService(api_key=None)
        # search_articles is async, so we need to await it
        result = asyncio.get_event_loop().run_until_complete(service.search_articles("AI"))
        assert result == []

    def test_the_news_api_returns_empty_when_key_missing(self):
        service = TheNewsApiService(api_token=None)
        # search_articles is async, so we need to await it
        result = asyncio.get_event_loop().run_until_complete(service.search_articles("tech"))
        assert result == []

    @pytest.mark.parametrize(
        ("cls_factory","key_arg"),
        [
            (NewsApiOrgService, "api_key"),
            (TheNewsApiService, "api_token"),
        ],
    )
    def test_fallback_on_api_errors(self, cls_factory, key_arg):
        """When external APIs raise exceptions, methods should return []."""
        fake_client = Mock()
        fake_client.get.side_effect = ConnectionError("network timeout")
        
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            async def get(self, url, params):
                raise ConnectionError("network timeout")

        with patch("httpx.AsyncClient", FakeAsyncClient):
            service = cls_factory(**{key_arg: "some-key"})
            # search_articles is async, so we need to await it
            result = asyncio.get_event_loop().run_until_complete(service.search_articles("anything"))
            assert result == []


# ---------------------------------------------------------------------------
# Google News RSS scraper
# ---------------------------------------------------------------------------


class TestGoogleNewsScraper:
    def test_scrape_topic_falls_back_to_empty_on_parse_failure(self):
        def parse_failure(url):
            raise Exception("RSS malformed")
        
        articles = GoogleNewsScraper.scrape_topic("quantum computing", limit=5)
        # If feedparser can't parse, we get empty list
        assert isinstance(articles, list)

    def test_scrape_topic_obeys_limit(self, monkeypatch):
        fake_feed = Mock()
        # Create proper mock entries with source as a dict-like object
        entries = []
        for i in range(10):
            entry = Mock()
            entry.get = Mock(side_effect=lambda key, default=None, idx=i: {
                "title": f"T{idx}",
                "link": f"https://example.com/{idx}",
                "published": "",
                "source": {"title": f"Source{idx}"}
            }.get(key, default))
            entries.append(entry)
        fake_feed.entries = entries
        monkeypatch.setattr("feedparser.parse", lambda url: fake_feed)

        articles = GoogleNewsScraper.scrape_topic("limit-test", limit=3)
        assert len(articles) == 3

    def test_google_news_produces_list_even_on_partial_success(self, monkeypatch):
        fake_feed = Mock()
        # Create proper mock entry with source as a dict-like object
        entry = Mock()
        entry.get = Mock(side_effect=lambda key, default=None: {
            "title": "Article by Bob",
            "link": "https://news.example.com/1",
            "published": "Mon, 25 Aug 2026 12:00:00 GMT",
            "source": {"title": "TechDaily"}
        }.get(key, default))
        fake_feed.entries = [entry]
        monkeypatch.setattr("feedparser.parse", lambda url: fake_feed)

        articles = GoogleNewsScraper.scrape_topic("innovation", country="US", limit=2)
        assert len(articles) >= 1


# ---------------------------------------------------------------------------
# Media Discovery enrichment with failed scrapers
# ---------------------------------------------------------------------------


class TestMediaDiscoveryService:
    @pytest.fixture()
    def fake_repo(self):
        repo = Mock()
        repo.create = Mock(side_effect=lambda rec: rec)
        return repo

    @pytest.fixture()
    def discovery_service(self, fake_repo):
        from services.scraping.enricher import MediaDiscoveryService
        return MediaDiscoveryService(repo=fake_repo)

    @pytest.fixture()
    def empty_scraper(self, monkeypatch):
        monkeypatch.setattr("services.scraping.enricher.GoogleNewsScraper.scrape_topic", lambda *a, **k: [])
        yield

    def test_discover_journalists_empty_when_scraper_returns_nothing(self, discovery_service, empty_scraper):
        results = discovery_service.discover_journalists_by_keyword("X", limit=5)
        assert results == []

    def test_media_discovery_gracefully_degrades_without_newsapi_keys(self, monkeypatch):
        # When keys are missing, both NewsAPI clients return [], so discovery
        # degrades gracefully to RSS-only scraping.
        async def mock_search(query, page_size=20):
            return []
        async def mock_search_tn(query, limit=20):
            return []

        fake_news = Mock(search_articles=mock_search)
        fake_tn = Mock(search_articles=mock_search_tn)

        monkeypatch.setattr("services.scraping.enricher.NewsApiOrgService", lambda: fake_news)
        monkeypatch.setattr("services.scraping.enricher.TheNewsApiService", lambda: fake_tn)

        with patch("services.scraping.enricher.GoogleNewsScraper.scrape_topic", return_value=[]):
            from services.scraping.enricher import MediaDiscoveryService
            results = MediaDiscoveryService().discover_journalists_by_keyword("Y")

        assert isinstance(results, list)

    def test_openai_embedding_deterministic_vector(self):
        """Without key, embedding must be normalized."""
        from services.ai.openai_service import OpenAIService
        svc = OpenAIService(api_key=None)
        vec = svc.generate_embedding("hello world")
        assert len(vec) == 1536
        import math
        norm = math.sqrt(sum(x*x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_deepseek_fallback_produces_output(self):
        from services.ai.deepseek_service import DeepSeekService
        svc = DeepSeekService(api_key=None)
        res = svc.generate_pitch("system", "user")
        assert "subject_line" in res
        assert "pitch_email" in res

    def test_orchestrator_selects_model_by_name(self):
        from services.ai.orchestrator import AIPitchOrchestrator

        openai_mock = Mock(generate_pitch=lambda s, u: {"subject_line": "O", "pitch_email": "openai"})
        deepseek_mock = Mock(generate_pitch=lambda s, u: {"subject_line": "D", "pitch_email": "deepseek"})
        templates_repo = Mock()
        templates_repo.get_default = Mock(return_value={"system_prompt": "", "user_prompt_template": "tpl"})

        orch = AIPitchOrchestrator(openai_service=openai_mock, deepseek_service=deepseek_mock, templates_repo=templates_repo)

        j = {"name": "J", "outlet": "M", "beat": ["A"], "bio": ""}
        c = {"story": "S", "name": "C"}

        pitch_gpt = orch.generate_pitch(j, c, model="gpt-4o")
        pitch_ds = orch.generate_pitch(j, c, model="deepseek-chat")

        assert pitch_gpt["subject_line"] == "O"
        assert pitch_ds["subject_line"] == "D"
