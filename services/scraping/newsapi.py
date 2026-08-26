"""Official NewsAPI.org and The News API integrations."""
import httpx
import logging
from typing import List, Dict, Any, Optional
from config.settings import get_settings

logger = logging.getLogger(__name__)


class NewsApiOrgService:
    """Client for NewsAPI.org."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.NEWS_API_ORG_KEY

    async def search_articles(self, query: str, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search top headlines and everything."""
        if not self.api_key:
            return []

        url = f"{self.BASE_URL}/everything"
        params = {
            "q": query,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    articles = []
                    for art in data.get("articles", []):
                        author = art.get("author") or "Editorial Team"
                        articles.append({
                            "author": author,
                            "title": art.get("title"),
                            "outlet": art.get("source", {}).get("name", "Unknown Outlet"),
                            "url": art.get("url"),
                            "published_at": art.get("publishedAt"),
                            "source": "newsapi"
                        })
                    return articles
        except Exception as e:
            logger.warning("NewsAPI request failed: %s", e)
        return []


class TheNewsApiService:
    """Client for TheNewsAPI.com."""

    BASE_URL = "https://api.thenewsapi.com/v1/news"

    def __init__(self, api_token: Optional[str] = None):
        settings = get_settings()
        self.api_token = api_token or settings.THE_NEWS_API_KEY

    async def search_articles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.api_token:
            return []

        url = f"{self.BASE_URL}/all"
        params = {
            "api_token": self.api_token,
            "search": query,
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    articles = []
                    for art in data.get("data", []):
                        articles.append({
                            "title": art.get("title"),
                            "outlet": art.get("source"),
                            "url": art.get("url"),
                            "published_at": art.get("published_at"),
                            "source": "thenewsapi"
                        })
                    return articles
        except Exception as e:
            logger.warning("TheNewsAPI request failed: %s", e)
        return []
