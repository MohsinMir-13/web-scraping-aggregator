"""
News/RSS scraper using feedparser (Google News and custom feeds).
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import feedparser
from urllib.parse import quote

from scrapers.base_scraper import BaseScraper
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class NewsScraper(BaseScraper):
    """Scraper for news via RSS feeds (Google News, custom feeds)."""

    def __init__(self):
        super().__init__("news")

    def validate_config(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        region: str = "lv",
        custom_feeds: Optional[List[str]] = None,
        language: str = "en"
    ) -> pd.DataFrame:
        """Search news using RSS feeds.

        Args:
            query: search terms
            limit: max items
            days_back: ignored by RSS, we'll filter by published date if provided
            region: ISO country code bias (e.g., lv for Latvia) for Google News
            custom_feeds: list of RSS feed URLs to include
            language: preferred language (en, lv)
        """
        feeds = []
        results: List[Dict[str, Any]] = []

        # Google News RSS (topic + region bias)
        # hl=language, gl=region, ceid=region:language
        gnews_base = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
        q = quote(query + " site:lv OR Latvia OR Riga")
        hl = "lv" if language == "lv" else "en"
        gl = region.lower()
        ceid = f"{region.lower()}:{hl}"
        feeds.append(gnews_base.format(q=q, hl=hl, gl=gl, ceid=ceid))

        # Add custom feeds if any
        if custom_feeds:
            feeds.extend(custom_feeds)

        try:
            for url in feeds:
                parsed = feedparser.parse(url)
                for entry in parsed.entries:
                    title = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    link = getattr(entry, "link", "")
                    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
                    try:
                        date = datetime(*entry.published_parsed[:6]) if getattr(entry, "published_parsed", None) else None
                    except Exception:
                        date = None

                    results.append({
                        "source": "news",
                        "title": title,
                        "body": summary,
                        "author": getattr(entry, "author", ""),
                        "date": date,
                        "url": link,
                        "score": 0,
                        "tags": [language, region]
                    })
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
        except Exception as e:
            self.logger.error(f"News RSS parsing failed: {e}")

        return pd.DataFrame(results[:limit])
