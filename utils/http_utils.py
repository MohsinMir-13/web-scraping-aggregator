"""
HTTP utilities and rate limiting.
"""
import asyncio
import time
from typing import Optional, Dict, Any
import aiohttp
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Simple rate limiter for HTTP requests."""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.last_request_time = 0
    
    async def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            wait_time = self.delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

class RobotsChecker:
    """Check robots.txt compliance."""
    
    def __init__(self):
        self._robots_cache = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
            
        Returns:
            True if URL can be fetched
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self._robots_cache:
                robots_url = urljoin(base_url, "/robots.txt")
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self._robots_cache[base_url] = rp
                except Exception:
                    # If robots.txt can't be read, assume fetching is allowed
                    logger.warning(f"Could not read robots.txt for {base_url}")
                    return True
            
            robots_parser = self._robots_cache[base_url]
            return robots_parser.can_fetch(user_agent, url)
        
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Default to allowing fetch if check fails

class HTTPClient:
    """HTTP client with rate limiting and robots.txt compliance."""
    
    def __init__(
        self,
        delay: float = 1.0,
        timeout: float = 30.0,
        user_agent: str = "WebScrapingAggregator/1.0",
        respect_robots: bool = True
    ):
        self.rate_limiter = RateLimiter(delay)
        self.robots_checker = RobotsChecker() if respect_robots else None
        self.timeout = timeout
        self.user_agent = user_agent
        
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Perform GET request with rate limiting and robots.txt check.
        
        Args:
            url: URL to fetch
            headers: Additional headers
            params: Query parameters
            
        Returns:
            Response object or None if blocked
        """
        # Check robots.txt
        if self.robots_checker and not self.robots_checker.can_fetch(url, self.user_agent):
            logger.warning(f"Blocked by robots.txt: {url}")
            return None
        
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        # Merge headers
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=request_headers, params=params) as response:
                    logger.debug(f"GET {url} -> {response.status}")
                    return response
        except Exception as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            return None
    
    def get_sync(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[requests.Response]:
        """
        Synchronous GET request with robots.txt check.
        
        Args:
            url: URL to fetch
            headers: Additional headers
            params: Query parameters
            
        Returns:
            Response object or None if blocked
        """
        # Check robots.txt
        if self.robots_checker and not self.robots_checker.can_fetch(url, self.user_agent):
            logger.warning(f"Blocked by robots.txt: {url}")
            return None
        
        # Merge headers
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            response = requests.get(
                url,
                headers=request_headers,
                params=params,
                timeout=self.timeout
            )
            logger.debug(f"GET {url} -> {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            return None

# Default HTTP client instance
default_http_client = HTTPClient()