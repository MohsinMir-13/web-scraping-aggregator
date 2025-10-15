"""
Scrapers package initialization.
"""
from .base_scraper import BaseScraper
from .reddit_scraper import RedditScraper
from .forum_scraper import ForumScraper
from .news_scraper import NewsScraper
from .classifieds_scraper import ClassifiedsScraper
from .suppliers_scraper import SuppliersScraper

__all__ = [
    "BaseScraper",
    "RedditScraper", 
    "ForumScraper",
    "NewsScraper",
    "ClassifiedsScraper",
    "SuppliersScraper"
]