"""
Reddit scraper using the official Reddit API via AsyncPRAW.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import asyncpraw
import aiohttp
from config.settings import API_CONFIG
from scrapers.base_scraper import BaseScraper
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class RedditScraper(BaseScraper):
    """Scraper for Reddit using PRAW (Python Reddit API Wrapper)."""
    
    def __init__(self):
        super().__init__("reddit")
        self.reddit = None
        self._reddit_connector: Optional[aiohttp.TCPConnector] = None
        self._reddit_session: Optional[aiohttp.ClientSession] = None
        # Initialization will be done in the first async call
    
    async def _initialize_client(self):
        """Initialize Reddit API client."""
        try:
            if self._reddit_connector is None:
                self._reddit_connector = aiohttp.TCPConnector(ssl=False)

            if self._reddit_session is None or self._reddit_session.closed:
                self._reddit_session = aiohttp.ClientSession(connector=self._reddit_connector)

            self.reddit = asyncpraw.Reddit(
                client_id=API_CONFIG.REDDIT_CLIENT_ID,
                client_secret=API_CONFIG.REDDIT_CLIENT_SECRET,
                user_agent=API_CONFIG.REDDIT_USER_AGENT,
                read_only=True,
                requestor_kwargs={"session": self._reddit_session}
            )
            self.logger.info("Reddit API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None
    
    def validate_config(self) -> bool:
        """Validate Reddit API configuration."""
        return (
            API_CONFIG.REDDIT_CLIENT_ID and
            API_CONFIG.REDDIT_CLIENT_SECRET and
            API_CONFIG.REDDIT_USER_AGENT
        )
    
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
        # Initialize client if not already done
        if not self.reddit:
            await self._initialize_client()
        
        if not self.reddit:
            self.logger.error("Reddit client not initialized")
            return pd.DataFrame()
        
        try:
            # Ensure we have a clean search
            results = await self._perform_search(query, limit, days_back, subreddits, sort)
            return results
        except Exception as e:
            self.logger.error(f"Reddit search encountered an error: {e}")
            return pd.DataFrame()
    
    async def _perform_search(
        self,
        query: str,
        limit: int,
        days_back: int,
        subreddits: Optional[List[str]],
        sort: str
    ) -> pd.DataFrame:
        """Perform the actual search using PRAW API."""
        self.logger.info(f"Searching Reddit for '{query}' (limit={limit}, days_back={days_back})")

        # Map days_back to PRAW time_filter values
        if days_back <= 1:
            time_filter = "day"
        elif days_back <= 7:
            time_filter = "week"
        elif days_back <= 30:
            time_filter = "month"
        elif days_back <= 365:
            time_filter = "year"
        else:
            time_filter = "all"

        try:
            posts = []

            if subreddits:
                # Search specific subreddits
                for subreddit_name in subreddits:
                    try:
                        subreddit = await self.reddit.subreddit(subreddit_name)
                        async for submission in subreddit.search(query, sort=sort, time_filter=time_filter, limit=limit):
                            post_data = self._extract_post_data(submission)
                            posts.append(post_data)
                            if len(posts) >= limit:
                                break
                    except Exception as e:
                        self.logger.warning(f"Error searching subreddit {subreddit_name}: {e}")
            else:
                # Search across multiple subreddits
                popular_subs = ['python', 'programming', 'learnpython', 'technology', 'datascience', 'webdev', 'javascript']
                posts_per_sub = max(limit // len(popular_subs), 3)

                for subreddit_name in popular_subs:
                    try:
                        subreddit = await self.reddit.subreddit(subreddit_name)
                        async for submission in subreddit.search(query, sort=sort, time_filter=time_filter, limit=posts_per_sub):
                            post_data = self._extract_post_data(submission)
                            posts.append(post_data)
                            if len(posts) >= limit:
                                break
                    except Exception as e:
                        self.logger.warning(f"Error searching subreddit {subreddit_name}: {e}")

            # Limit results and sort by score (most relevant first)
            posts = posts[:limit]
            posts.sort(key=lambda x: x.get('score', 0), reverse=True)

            self.logger.info(f"Found {len(posts)} Reddit posts")
            return pd.DataFrame(posts)

        except Exception as e:
            self.logger.error(f"Reddit search failed: {e}")
            return pd.DataFrame()
    
    async def _search_subreddit_http(
        self,
        session,
        subreddit_name: str,
        query: str,
        limit: int,
        start_date: datetime,
        sort: str
    ) -> List[Dict[str, Any]]:
        """Search a subreddit using HTTP requests."""
        posts = []
        
        try:
            # Use Reddit's JSON API
            url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
            params = {
                'q': query,
                'limit': min(limit, 25),  # Reddit limits to 25 per request
                'restrict_sr': 'on',
                'sort': 'relevance' if sort == 'relevance' else 'new',
                't': 'month'
            }
            
            headers = {'User-Agent': API_CONFIG.REDDIT_USER_AGENT}
            
            async with session.get(url, params=params, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('data', {}).get('children', []):
                        post_data = item.get('data', {})
                        post_date = datetime.fromtimestamp(post_data.get('created_utc', 0))
                        
                        if post_date >= start_date:
                            posts.append({
                                'title': post_data.get('title', ''),
                                'selftext': post_data.get('selftext', ''),
                                'author': post_data.get('author', '[deleted]'),
                                'created_utc': post_data.get('created_utc', 0),
                                'score': post_data.get('score', 0),
                                'num_comments': post_data.get('num_comments', 0),
                                'url': post_data.get('url', ''),
                                'permalink': f"https://reddit.com{post_data.get('permalink', '')}",
                                'subreddit': subreddit_name,
                                'source': 'reddit'
                            })
                else:
                    self.logger.warning(f"Reddit API returned status {response.status} for r/{subreddit_name}")
                    
        except Exception as e:
            self.logger.error(f"Error searching r/{subreddit_name}: {e}")
        
        return posts
    
    async def cleanup(self):
        """Clean up the Reddit client session."""
        # For read-only mode, no cleanup needed
        if self.reddit and self.reddit != "read_only":
            try:
                await self.reddit.close()
            except Exception as e:
                self.logger.error(f"Error closing Reddit client: {e}")
            finally:
                self.reddit = None

        if self._reddit_session:
            try:
                await self._reddit_session.close()
            except Exception as e:
                self.logger.error(f"Error closing Reddit session: {e}")
            finally:
                self._reddit_session = None

        if self._reddit_connector:
            try:
                await self._reddit_connector.close()
            except Exception as e:
                self.logger.error(f"Error closing Reddit connector: {e}")
            finally:
                self._reddit_connector = None
    
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
            
            async for submission in search_results:
                post_date = datetime.fromtimestamp(submission.created_utc)
                if post_date >= start_date:
                    post_data = await self._extract_post_data(submission)
                    posts.append(post_data)
        
        except Exception as e:
            self.logger.warning(f"Error searching subreddit: {e}")
        
        return posts
    
    async def _extract_post_data(self, submission) -> Dict[str, Any]:
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