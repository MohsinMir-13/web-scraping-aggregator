"""
Configuration settings for the web scraping application.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class ScrapingConfig:
    """Configuration for scraping parameters."""
    
    # Rate limiting
    REQUEST_DELAY: float = 1.0
    MAX_CONCURRENT_REQUESTS: int = 10
    TIMEOUT: float = 30.0
    
    # Result limits
    DEFAULT_LIMIT: int = 50
    MAX_LIMIT: int = 500
    
    # Date ranges
    DEFAULT_DAYS_BACK: int = 30
    MAX_DAYS_BACK: int = 365

@dataclass
class APIConfig:
    """API configuration and credentials."""
    
    # Reddit API
    REDDIT_CLIENT_ID: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT: str = os.getenv('REDDIT_USER_AGENT', 'WebScrapingAggregator/1.0')
    
    # GitHub API
    GITHUB_TOKEN: Optional[str] = os.getenv('GITHUB_TOKEN')
    
    # Stack Exchange API
    STACKEXCHANGE_KEY: Optional[str] = os.getenv('STACKEXCHANGE_KEY')

@dataclass
class DatabaseConfig:
    """Database configuration (optional)."""
    
    # MongoDB
    MONGODB_URI: Optional[str] = os.getenv('MONGODB_URI')
    MONGODB_DB_NAME: str = os.getenv('MONGODB_DB_NAME', 'web_scraping')
    
    # PostgreSQL
    POSTGRES_URI: Optional[str] = os.getenv('POSTGRES_URI')

# Global configuration instances
SCRAPING_CONFIG = ScrapingConfig()
API_CONFIG = APIConfig()
DB_CONFIG = DatabaseConfig()

# Streamlit page configuration
STREAMLIT_CONFIG = {
    "page_title": "Web Scraping Aggregator",
    "page_icon": "🕷️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Supported data sources
DATA_SOURCES = {
    "reddit": "Reddit",
    "github": "GitHub Issues/Discussions", 
    "stackoverflow": "Stack Overflow",
    "forums": "Generic Forums"
}

# Standard field mapping for normalization
STANDARD_FIELDS = [
    "source",
    "title", 
    "body",
    "author",
    "date",
    "url",
    "score",
    "comments_count",
    "tags"
]