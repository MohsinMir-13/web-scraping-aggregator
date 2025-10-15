"""
Suppliers scraper: searches product catalogs for construction materials.
Targets: K-Senukai (ksenukai.lv) and Stokker (stokker.com/lv).
"""
from typing import List, Dict, Any
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import asyncio
from datetime import datetime

from scrapers.base_scraper import BaseScraper
from utils.http_utils import HTTPClient
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class SuppliersScraper(BaseScraper):
    def __init__(self):
        super().__init__("suppliers")
        self.http = HTTPClient(delay=1.5, respect_robots=False)

    def validate_config(self) -> bool:
        return True

    async def search(self, query: str, limit: int = 50, days_back: int = 30, sites: list[str] | None = None) -> pd.DataFrame:
        results: List[Dict[str, Any]] = []
        try:
            # Normalize site selection
            selected = set(sites or ["K-Senukai", "Stokker"])

            # 1) K-Senukai search
            if "K-Senukai" in selected:
                q = quote_plus(query)
                k_url = f"https://www.ksenukai.lv/lv/search/?q={q}"
                k_resp = await asyncio.to_thread(self.http.get_sync, k_url)
                if k_resp and k_resp.status_code == 200:
                    k_soup = BeautifulSoup(k_resp.text, 'html.parser')
                    for item in k_soup.select('[data-el="product"]'):
                        title_el = item.select_one('[data-el="product-title"]')
                        price_el = item.select_one('[data-el="product-price-current"]')
                        link_el = item.select_one('a')
                        title = title_el.get_text(strip=True) if title_el else (link_el.get_text(strip=True) if link_el else "")
                        href = urljoin("https://www.ksenukai.lv", link_el['href']) if link_el and link_el.get('href') else k_url
                        price = price_el.get_text(strip=True) if price_el else ""
                        if title:
                            results.append({
                                "source": "suppliers",
                                "title": title,
                                "body": price,
                                "author": "K-Senukai",
                                "date": datetime.now(),
                                "url": href,
                                "score": 0,
                                "tags": ["ksenukai"]
                            })
                        if len(results) >= limit:
                            return pd.DataFrame(results)

            # 2) Stokker search
            if "Stokker" in selected:
                q = quote_plus(query)
                s_url = f"https://www.stokker.com/lv/search?q={q}"
                s_resp = await asyncio.to_thread(self.http.get_sync, s_url)
                if s_resp and s_resp.status_code == 200:
                    s_soup = BeautifulSoup(s_resp.text, 'html.parser')
                    for item in s_soup.select('.product-list-item, .product-card'):
                        title_el = item.select_one('.product-title, .title a, a')
                        price_el = item.select_one('.price, .product-price')
                        title = title_el.get_text(strip=True) if title_el else ""
                        href = urljoin("https://www.stokker.com", title_el['href']) if title_el and title_el.get('href') else s_url
                        price = price_el.get_text(strip=True) if price_el else ""
                        if title:
                            results.append({
                                "source": "suppliers",
                                "title": title,
                                "body": price,
                                "author": "Stokker",
                                "date": datetime.now(),
                                "url": href,
                                "score": 0,
                                "tags": ["stokker"]
                            })
                        if len(results) >= limit:
                            break

        except Exception as e:
            self.logger.error(f"Suppliers scrape failed: {e}")

        return pd.DataFrame(results[:limit])
