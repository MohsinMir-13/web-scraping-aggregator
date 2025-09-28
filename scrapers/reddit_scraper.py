"""
Reddit scraper using the official Reddit API via PRAW.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import praw
from config.settings import API_CONFIG
from scrapers.base_scraper import BaseScraper
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class RedditScraper(BaseScraper):
    """Scraper for Reddit using PRAW (Python Reddit API Wrapper)."""
    
    def __init__(self):
        super().__init__("reddit")
        self.reddit = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Reddit API client."""
        try:
            if API_CONFIG.REDDIT_CLIENT_ID and API_CONFIG.REDDIT_CLIENT_SECRET:
                self.reddit = praw.Reddit(
                    client_id=API_CONFIG.REDDIT_CLIENT_ID,
                    client_secret=API_CONFIG.REDDIT_CLIENT_SECRET,
                    user_agent=API_CONFIG.REDDIT_USER_AGENT
                )
                self.logger.info("Reddit API client initialized successfully")
            else:
                self.logger.warning("Reddit API credentials not found. Using read-only mode.")
                # Fallback to read-only mode (limited functionality)
                self.reddit = praw.Reddit(
                    client_id="dummy",
                    client_secret="dummy", 
                    user_agent=API_CONFIG.REDDIT_USER_AGENT
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None
    
    def validate_config(self) -> bool:
        """Validate Reddit API configuration."""
        return self.reddit is not None
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        subreddits: Optional[List[str]] = None,
        sort: str = "relevance",
        **kwargs
    ) -> pd.DataFrame:
        """
        Search Reddit for posts matching the query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            days_back: Days to search back
            subreddits: Specific subreddits to search (None for all)
            sort: Sort method ('relevance', 'hot', 'new', 'top')
            
        Returns:
            DataFrame with Reddit posts
        """
        if not self.reddit:
            self.logger.error("Reddit client not initialized")
            return pd.DataFrame()
        
        self.logger.info(f"Searching Reddit for '{query}' (limit={limit}, days_back={days_back})")
        
        try:
            posts = []
            start_date, end_date = self.get_date_range(days_back)
            
            # Search in specific subreddits or all of Reddit
            if subreddits:
                for subreddit_name in subreddits:
                    try:
                        subreddit = self.reddit.subreddit(subreddit_name)
                        subreddit_posts = await self._search_subreddit(
                            subreddit, query, limit // len(subreddits), start_date, sort
                        )
                        posts.extend(subreddit_posts)
                    except Exception as e:
                        self.logger.warning(f"Error searching subreddit {subreddit_name}: {e}")
            else:
                # Search all of Reddit
                try:
                    search_results = self.reddit.subreddit("all").search(
                        query, limit=limit, sort=sort, time_filter="month"
                    )
                    
                    for submission in search_results:
                        post_date = datetime.fromtimestamp(submission.created_utc)
                        if start_date <= post_date <= end_date:
                            post_data = self._extract_post_data(submission)
                            posts.append(post_data)
                        
                        if len(posts) >= limit:
                            break
                
                except Exception as e:
                    self.logger.error(f"Error searching Reddit: {e}")
            
            self.logger.info(f"Found {len(posts)} Reddit posts")
            return pd.DataFrame(posts)
        
        except Exception as e:
            self.logger.error(f"Reddit search failed: {e}")
            return pd.DataFrame()
    
    async def _search_subreddit(
        self,
        subreddit,
        query: str,
        limit: int,
        start_date: datetime,
        sort: str
    ) -> List[Dict[str, Any]]:
        """Search within a specific subreddit."""
        posts = []
        
        try:
            search_results = subreddit.search(
                query, limit=limit, sort=sort, time_filter="month"
            )
            
            for submission in search_results:
                post_date = datetime.fromtimestamp(submission.created_utc)
                if post_date >= start_date:
                    post_data = self._extract_post_data(submission)
                    posts.append(post_data)
        
        except Exception as e:
            self.logger.warning(f"Error searching subreddit: {e}")
        
        return posts
    
    def _extract_post_data(self, submission) -> Dict[str, Any]:
        """Extract data from a Reddit submission."""
        try:
            return {
                "title": submission.title,
                "selftext": submission.selftext,
                "author": str(submission.author) if submission.author else "[deleted]",
                "created_utc": submission.created_utc,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "url": f"https://reddit.com{submission.permalink}",
                "subreddit": str(submission.subreddit),
                "id": submission.id,
                "upvote_ratio": getattr(submission, "upvote_ratio", None),
                "is_self": submission.is_self,
                "domain": submission.domain,
                "thumbnail": getattr(submission, "thumbnail", ""),
                "link_flair_text": getattr(submission, "link_flair_text", ""),
                "gilded": getattr(submission, "gilded", 0)
            }
        except Exception as e:
            self.logger.warning(f"Error extracting post data: {e}")
            return {}
    
    async def get_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 50,
        sort: str = "hot"
    ) -> pd.DataFrame:
        """
        Get posts from a specific subreddit.
        
        Args:
            subreddit_name: Name of the subreddit
            limit: Number of posts to fetch
            sort: Sort method ('hot', 'new', 'top', 'rising')
            
        Returns:
            DataFrame with subreddit posts
        """
        if not self.reddit:
            return pd.DataFrame()
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            if sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "new":
                submissions = subreddit.new(limit=limit)
            elif sort == "top":
                submissions = subreddit.top(limit=limit, time_filter="month")
            elif sort == "rising":
                submissions = subreddit.rising(limit=limit)
            else:
                submissions = subreddit.hot(limit=limit)
            
            for submission in submissions:
                post_data = self._extract_post_data(submission)
                posts.append(post_data)
            
            self.logger.info(f"Retrieved {len(posts)} posts from r/{subreddit_name}")
            return pd.DataFrame(posts)
        
        except Exception as e:
            self.logger.error(f"Error fetching subreddit posts: {e}")
            return pd.DataFrame()