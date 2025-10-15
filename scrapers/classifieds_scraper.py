"""
Classifieds scraper for ss.com (Latvia). Parses search results for requests/offers.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from datetime import datetime
import asyncio

from scrapers.base_scraper import BaseScraper
from utils.http_utils import HTTPClient
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class ClassifiedsScraper(BaseScraper):
    def __init__(self):
        super().__init__("classifieds")
        self.http = HTTPClient(delay=1.5, respect_robots=False)
        self.base = "https://www.ss.com"

    def validate_config(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        category: str = "services/search/",
        region: str = "riga/"
    ) -> pd.DataFrame:
        # Build search URL for ss.com
        # Example: https://www.ss.com/lv/search/?q=jumta+remonts
        q = quote_plus(query)
        url = f"{self.base}/lv/search/?q={q}"
        try:
            resp = await asyncio.to_thread(self.http.get_sync, url)
            if not resp or resp.status_code != 200:
                self.logger.warning(f"SS.com request failed: {resp.status_code if resp else 'no response'}")
                return pd.DataFrame()

            soup = BeautifulSoup(resp.text, 'html.parser')
            table = soup.find('table', id='filter_tbl')
            results: List[Dict[str, Any]] = []

            # Listings rows often in tables with class 'msga2' etc.
            for row in soup.select('tr.msga2, tr.msga2-o'):
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                link_tag = cols[1].find('a')
                title = link_tag.get_text(strip=True) if link_tag else cols[1].get_text(strip=True)
                href = urljoin(self.base, link_tag['href']) if link_tag and link_tag.get('href') else url
                price = cols[-1].get_text(strip=True)
                location = cols[-2].get_text(strip=True) if len(cols) >= 2 else ""
                date_str = cols[0].get_text(strip=True)

                results.append({
                    "source": "classifieds",
                    "title": title,
                    "body": f"{location} | {price}",
                    "author": "",
                    "date": datetime.now(),
                    "url": href,
                    "score": 0,
                    "tags": ["ss.com", region]
                })
                if len(results) >= limit:
                    break

            return pd.DataFrame(results)
        except Exception as e:
            self.logger.error(f"SS.com scrape failed: {e}")
            return pd.DataFrame()
