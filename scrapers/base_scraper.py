"""
Base scraper class defining the interface for all scrapers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"scraper.{name}")
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        **kwargs
    ) -> pd.DataFrame:
        """
        Search for content based on query.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            days_back: How many days back to search
            **kwargs: Additional source-specific parameters
            
        Returns:
            DataFrame with raw results
        """
        pass
    
    def get_date_range(self, days_back: int) -> tuple[datetime, datetime]:
        """Get date range for search."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date
    
    def validate_config(self) -> bool:
        """Validate scraper configuration."""
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """Get scraper information."""
        return {
            "name": self.name,
            "configured": self.validate_config()
        }