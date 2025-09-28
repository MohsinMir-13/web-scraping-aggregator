"""
Configuration settings for the web scraping application.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Try to import streamlit for secrets, fallback to dotenv
try:
    import streamlit as st
    USE_STREAMLIT_SECRETS = True
except ImportError:
    USE_STREAMLIT_SECRETS = False

# Load environment variables
load_dotenv()

def get_secret(key: str, default: str = None) -> Optional[str]:
    """Get secret from Streamlit secrets or environment variables."""
    if USE_STREAMLIT_SECRETS:
        try:
            return st.secrets.get(key, default)
        except (AttributeError, FileNotFoundError):
            # Fallback to environment variables if secrets not available
            return os.getenv(key, default)
    return os.getenv(key, default)

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
    
        # Reddit API Configuration
    REDDIT_CLIENT_ID: Optional[str] = get_secret('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET: Optional[str] = get_secret('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT: str = get_secret('REDDIT_USER_AGENT', 'WebScrapingAggregator/1.0')
    
    # GitHub API Configuration
    GITHUB_TOKEN: Optional[str] = get_secret('GITHUB_TOKEN')
    
    # Stack Exchange API Configuration
    STACKEXCHANGE_KEY: Optional[str] = get_secret('STACKEXCHANGE_KEY')

@dataclass
class DatabaseConfig:
    """Database configuration (optional)."""
    
    # Database Configuration
    MONGODB_URI: Optional[str] = get_secret('MONGODB_URI')
    MONGODB_DB_NAME: str = get_secret('MONGODB_DB_NAME', 'web_scraping')
    
    # PostgreSQL Configuration
    POSTGRES_URI: Optional[str] = get_secret('POSTGRES_URI')

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