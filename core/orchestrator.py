"""
Core orchestrator for coordinating scraping operations across multiple sources.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time

from scrapers import RedditScraper, ForumScraper, NewsScraper, ClassifiedsScraper, SuppliersScraper
from utils.data_utils import DataNormalizer, merge_dataframes
from utils.logging_utils import get_logger
from config.settings import SCRAPING_CONFIG, DATA_SOURCES

logger = get_logger(__name__)

class ScrapingOrchestrator:
    """Orchestrates scraping operations across multiple data sources."""
    
    def __init__(self):
        self.scrapers = {
            "reddit": RedditScraper(),
            "forums": ForumScraper(),
            "news": NewsScraper(),
            "classifieds": ClassifiedsScraper(),
            "suppliers": SuppliersScraper()
        }
        self.normalizer = DataNormalizer()
        self.results_cache = {}
    
    async def search_all_sources(
        self,
        query: str,
        selected_sources: List[str],
        limit_per_source: int = 50,
        days_back: int = 30,
        source_params: Optional[Dict[str, Dict]] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Search across multiple sources concurrently.
        
        Args:
            query: Search query string
            selected_sources: List of source names to search
            limit_per_source: Maximum results per source
            days_back: Days to search back
            source_params: Source-specific parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (merged_dataframe, metadata)
        """
        start_time = time.time()
        
        logger.info(f"Starting search for '{query}' across {len(selected_sources)} sources")
        # Debug: record initial query for transparency
        logger.debug({"event": "search_start", "query": query, "sources": selected_sources, "limit_per_source": limit_per_source})
        
        if progress_callback:
            progress_callback(0, f"Initializing search for '{query}'...")
        
        # Validate sources
        valid_sources = [src for src in selected_sources if src in self.scrapers]
        if not valid_sources:
            logger.error("No valid sources selected")
            return pd.DataFrame(), {"error": "No valid sources selected"}
        
        # Prepare source parameters
        if source_params is None:
            source_params = {}
        
        # Create tasks for concurrent execution
        tasks = []
        for i, source in enumerate(valid_sources):
            scraper = self.scrapers[source]
            params = source_params.get(source, {})
            
            task = self._search_source_with_progress(
                scraper, source, query, limit_per_source, days_back,
                params, progress_callback, i, len(valid_sources)
            )
            tasks.append(task)
        
        # Execute searches concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in concurrent search execution: {e}")
            return pd.DataFrame(), {"error": str(e)}
        
        # Process results
        source_dataframes = []
        source_metadata = {}
        
        for i, result in enumerate(results):
            source = valid_sources[i]
            
            if isinstance(result, Exception):
                logger.error(f"Error searching {source}: {result}")
                source_metadata[source] = {
                    "success": False,
                    "error": str(result),
                    "count": 0
                }
            else:
                df, metadata = result
                source_dataframes.append(df)
                source_metadata[source] = metadata
        
        # Merge all results
        if progress_callback:
            progress_callback(90, "Merging and normalizing results...")
        
        merged_df = merge_dataframes(source_dataframes)
        
        # Calculate overall metadata
        total_time = time.time() - start_time
        overall_metadata = {
            "query": query,
            "sources_searched": valid_sources,
            "total_results": len(merged_df),
            "search_time_seconds": round(total_time, 2),
            "source_results": source_metadata,
            "search_timestamp": datetime.now().isoformat()
        }
        
        if progress_callback:
            progress_callback(100, f"Search completed! Found {len(merged_df)} total results.")
        
        logger.info(f"Search completed in {total_time:.2f}s. Total results: {len(merged_df)}")
        
        return merged_df, overall_metadata
    
    async def _search_source_with_progress(
        self,
        scraper,
        source: str,
        query: str,
        limit: int,
        days_back: int,
        params: Dict,
        progress_callback: Optional[callable],
        source_index: int,
        total_sources: int
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Search a single source with progress reporting."""
        start_time = time.time()
        
        try:
            if progress_callback:
                progress = int((source_index / total_sources) * 80)  # 80% for searching
                progress_callback(progress, f"Searching {DATA_SOURCES.get(source, source)}...")
            
            # Perform the search
            raw_df = await scraper.search(
                query=query,
                limit=limit,
                days_back=days_back,
                **params
            )
            
            # Normalize the data
            normalized_df = self.normalizer.normalize_dataframe(raw_df, source)
            
            # Create metadata
            search_time = time.time() - start_time
            metadata = {
                "success": True,
                "count": len(normalized_df),
                "search_time_seconds": round(search_time, 2),
                "scraper_configured": scraper.validate_config()
            }
            
            logger.info(f"{source.capitalize()} search completed: {len(normalized_df)} results in {search_time:.2f}s")
            
            return normalized_df, metadata
        
        except Exception as e:
            error_msg = f"Error searching {source}: {str(e)}"
            logger.error(error_msg)
            
            return pd.DataFrame(), {
                "success": False,
                "error": str(e),
                "count": 0,
                "search_time_seconds": time.time() - start_time,
                "scraper_configured": scraper.validate_config()
            }
    
    def get_scraper_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all scrapers."""
        status = {}
        
        for source, scraper in self.scrapers.items():
            status[source] = {
                "name": DATA_SOURCES.get(source, source),
                "configured": scraper.validate_config(),
                "available": True
            }
        
        return status
    
    async def search_single_source(
        self,
        source: str,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        **kwargs
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Search a single source.
        
        Args:
            source: Source name
            query: Search query
            limit: Result limit
            days_back: Days to search back
            **kwargs: Source-specific parameters
            
        Returns:
            Tuple of (dataframe, metadata)
        """
        if source not in self.scrapers:
            error_msg = f"Unknown source: {source}"
            logger.error(error_msg)
            return pd.DataFrame(), {"error": error_msg}
        
        scraper = self.scrapers[source]
        
        try:
            start_time = time.time()
            
            # Perform search
            raw_df = await scraper.search(
                query=query,
                limit=limit,
                days_back=days_back,
                **kwargs
            )
            
            # Normalize data
            normalized_df = self.normalizer.normalize_dataframe(raw_df, source)
            
            # Create metadata
            search_time = time.time() - start_time
            metadata = {
                "success": True,
                "source": source,
                "query": query,
                "count": len(normalized_df),
                "search_time_seconds": round(search_time, 2),
                "scraper_configured": scraper.validate_config()
            }
            
            return normalized_df, metadata
        
        except Exception as e:
            error_msg = f"Error searching {source}: {str(e)}"
            logger.error(error_msg)
            
            return pd.DataFrame(), {
                "success": False,
                "error": str(e),
                "source": source,
                "count": 0,
                "scraper_configured": scraper.validate_config()
            }
    
    def filter_results(
        self,
        df: pd.DataFrame,
        source_filter: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        min_score: Optional[int] = None,
        keyword_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Filter search results based on various criteria.
        
        Args:
            df: DataFrame to filter
            source_filter: Filter by sources
            date_range: Filter by date range (start, end)
            min_score: Minimum score filter
            keyword_filter: Keyword to search in title/body
            
        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
        # Filter by source
        if source_filter:
            filtered_df = filtered_df[filtered_df["source"].isin(source_filter)]
        
        # Filter by date range
        if date_range and "date" in filtered_df.columns:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df["date"] >= start_date) & 
                (filtered_df["date"] <= end_date)
            ]
        
        # Filter by minimum score
        if min_score is not None and "score" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["score"] >= min_score]
        
        # Filter by keyword
        if keyword_filter:
            keyword_lower = keyword_filter.lower()
            mask = (
                filtered_df["title"].str.lower().str.contains(keyword_lower, na=False) |
                filtered_df["body"].str.lower().str.contains(keyword_lower, na=False)
            )
            filtered_df = filtered_df[mask]
        
        logger.info(f"Filtered {len(df)} results down to {len(filtered_df)}")
        
        return filtered_df.reset_index(drop=True)
    
    def get_search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions based on query."""
        suggestions = []
        
        # Add query variations
        query_words = query.lower().split()
        
        if len(query_words) > 1:
            # Add individual words
            suggestions.extend([f'"{word}"' for word in query_words if len(word) > 3])
            
            # Add combinations
            for i in range(len(query_words) - 1):
                combo = " ".join(query_words[i:i+2])
                suggestions.append(f'"{combo}"')
        
        # Add common construction/roofing terms if the query appears related (heuristic)
        construction_indicators = {"roof", "construction", "building", "contractor", "repair", "install", "material", "Latvia", "Riga"}
        query_tokens = set(query_words)
        if query_tokens & construction_indicators:
            construction_terms = ["Latvia", "Riga", "contractor", "installation", "repair", "materials", "cost"]
            for term in construction_terms:
                if term.lower() not in query.lower():
                    suggestions.append(f"{query} {term}")
        
        return suggestions[:10]  # Limit to 10 suggestions

# Global orchestrator instance
orchestrator = ScrapingOrchestrator()