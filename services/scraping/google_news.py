"""Google News RSS Scraper (Free, no API key required)."""
import urllib.parse
import feedparser
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class GoogleNewsScraper:
    """Scrapes Google News RSS for journalist and outlet intelligence."""

    BASE_RSS_URL = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"

    @classmethod
    def scrape_topic(
        cls,
        keyword: str,
        lang: str = "en",
        country: str = "US",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Scrape articles matching a keyword topic."""
        encoded_query = urllib.parse.quote(keyword)
        hl = f"{lang}-{country}"
        gl = country
        ceid = f"{country}:{lang}"

        url = cls.BASE_RSS_URL.format(query=encoded_query, hl=hl, gl=gl, ceid=ceid)

        try:
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                source_name = entry.get("source", {}).get("title", "")

                # Google News titles are usually in the form: "Article Title - Outlet Name"
                outlet = source_name
                headline = title
                if " - " in title and not source_name:
                    parts = title.rsplit(" - ", 1)
                    headline = parts[0]
                    outlet = parts[1]

                articles.append({
                    "title": headline,
                    "outlet": outlet or "News Media",
                    "url": link,
                    "published_at": published,
                    "beat": [keyword.lower()],
                    "source": "googlenews"
                })

            return articles
        except Exception as e:
            logger.error("Failed to parse Google News RSS: %s", e)
            return []
