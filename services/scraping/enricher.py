"""Journalist enrichment and evidence-first discovery coordinator."""
import re
from typing import List, Dict, Any, Optional
from services.scraping.google_news import GoogleNewsScraper
from services.scraping.newsapi import NewsApiOrgService, TheNewsApiService
from core.scoring import calculate_4d_score
from db.repositories.journalists_repo import JournalistsRepository


class MediaDiscoveryService:
    """Discovers and enriches journalist data from news feeds."""

    def __init__(self, repo: Optional[JournalistsRepository] = None):
        self.repo = repo or JournalistsRepository()
        self.google_scraper = GoogleNewsScraper()
        self.newsapi = NewsApiOrgService()
        self.thenewsapi = TheNewsApiService()

    def discover_journalists_by_keyword(
        self,
        keyword: str,
        country: str = "US",
        limit: int = 10,
        auto_save: bool = True
    ) -> List[Dict[str, Any]]:
        """Return coverage candidates without inventing contact information.

        Article feeds are useful evidence for names, outlets, beats and recent
        work, but they are not evidence of an email address. Candidates are
        therefore not persisted until a public or provider-verified address is
        supplied with its source.
        """
        articles = self.google_scraper.scrape_topic(keyword=keyword, country=country, limit=limit)
        
        discovered = []
        for art in articles:
            outlet = art.get("outlet", "News Desk")
            title = art.get("title", "")
            
            # Simple author byline extraction heuristic
            inferred_name = f"Reporter ({outlet})"
            if "by " in title.lower():
                parts = title.lower().split("by ", 1)
                inferred_name = parts[1].split("-")[0].strip().title()

            candidate = {
                "name": inferred_name,
                "email": None,
                "email_status": "missing",
                "email_source_url": None,
                "outlet": outlet,
                "beat": [keyword.lower()],
                "bio": f"Recent article: '{title}'",
                "recent_articles": [{"title": title, "url": art.get("url"), "source": art.get("source")}],
                "source": "googlenews",
                "persisted": False,
                "review_note": "Add only after finding a public or provider-verified email and recording its source.",
            }
            
            # Calculate initial 4D score
            scores = calculate_4d_score(candidate, target_beats=[keyword])
            candidate.update(scores)
            
            # ``auto_save`` remains in the public API for compatibility, but a
            # candidate with no evidenced email must never enter the outreach
            # database automatically.
            discovered.append(candidate)

        return discovered
