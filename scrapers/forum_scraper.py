"""
Generic forum scraper using HTML parsing with BeautifulSoup.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from scrapers.base_scraper import BaseScraper
from utils.http_utils import HTTPClient
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class ForumScraper(BaseScraper):
    """Generic scraper for HTML-based forums and discussion boards."""
    
    def __init__(self):
        super().__init__("forums")
        self.http_client = HTTPClient(delay=2.0, respect_robots=False)  # More conservative rate limiting, disable robots checking
        
        # Common forum patterns and selectors
        self.forum_patterns = {
            "discourse": {
                "search_url": "/search?q={query}",
                "post_selector": ".fps-result",
                "title_selector": ".fps-topic",
                "content_selector": ".fps-post",
                "author_selector": ".username",
                "date_selector": ".relative-date"
            },
            "phpbb": {
                "search_url": "/search.php?keywords={query}",
                "post_selector": ".post",
                "title_selector": ".post-subject",
                "content_selector": ".post-text",
                "author_selector": ".username",
                "date_selector": ".post-date"
            },
            "vbulletin": {
                "search_url": "/search.php?do=process&query={query}",
                "post_selector": ".post",
                "title_selector": ".title",
                "content_selector": ".post-content",
                "author_selector": ".username",
                "date_selector": ".post-date"
            },
            "generic": {
                "post_selector": "article, .post, .topic, .message",
                "title_selector": "h1, h2, h3, .title, .subject",
                "content_selector": ".content, .message, .post-content, p",
                "author_selector": ".author, .username, .user",
                "date_selector": ".date, .timestamp, time"
            }
        }
    
    def validate_config(self) -> bool:
        """Forum scraper doesn't require specific configuration."""
        return True
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        forum_urls: Optional[List[str]] = None,
        forum_type: str = "auto",
        **kwargs
    ) -> pd.DataFrame:
        """
        Search forums for posts matching the query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            days_back: Days to search back (may not be supported by all forums)
            forum_urls: List of forum URLs to search
            forum_type: Forum type ('discourse', 'phpbb', 'vbulletin', 'generic', 'auto')
            
        Returns:
            DataFrame with forum posts
        """
        if not forum_urls:
            # Use default forum URLs
            from config.settings import DEFAULT_FORUM_URLS
            forum_urls = DEFAULT_FORUM_URLS
            self.logger.info(f"Using default forum URLs: {len(forum_urls)} forums")
        
        self.logger.info(f"Searching {len(forum_urls)} forums for '{query}' (limit={limit})")
        
        all_posts = []
        
        for forum_url in forum_urls:
            try:
                per_forum_limit = max(3, limit // len(forum_urls))
                forum_posts = await self._search_forum(
                    forum_url.rstrip('/'), query, per_forum_limit, forum_type
                )
                if not forum_posts:
                    self.logger.debug(f"No posts via recent scrape, trying generic search for {forum_url}")
                    generic_extra = await self._search_forum_generic(forum_url.rstrip('/'), query, per_forum_limit)
                    forum_posts.extend(generic_extra)
                all_posts.extend(forum_posts)
            except Exception as e:
                self.logger.warning(f"Error searching forum {forum_url}: {e}")
        
        # Sort by relevance/date if possible
        all_posts = sorted(all_posts, key=lambda x: x.get("date", datetime.min), reverse=True)
        
        # Limit results
        all_posts = all_posts[:limit]
        
        self.logger.info(f"Found {len(all_posts)} forum posts total")
        if not all_posts:
            self.logger.debug("Forum scraper returned zero posts. Consider adding more specific forum URLs or relaxing keyword filtering.")
        return pd.DataFrame(all_posts)
    
    async def _search_forum(
        self,
        forum_url: str,
        query: str,
        limit: int,
        forum_type: str
    ) -> List[Dict[str, Any]]:
        """Search a specific forum by scraping recent posts."""
        posts = []

        try:
            # For forums, we'll scrape recent posts instead of searching
            # since most forums don't have good search functionality
            self.logger.info(f"Scraping recent posts from {forum_url}")

            # Get the forum homepage
            response = await asyncio.to_thread(self.http_client.get_sync, forum_url)
            if not response or response.status_code != 200:
                self.logger.warning(f"Failed to access {forum_url}")
                return posts

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try different selectors for finding posts/threads
            post_selectors = [
                '.topic-list-item',
                'tr.topic-list-item',
                'li.topic-list-item',
                '.latest-topic-list-item',
                '.post',
                '.thread',
                'article',
                '.discussion',
                'h2',
                'h2 a',
                '.title a'
            ]

            found_posts = []

            for selector in post_selectors:
                elements = soup.select(selector)
                if not elements:
                    continue
                for element in elements[: limit * 2]:
                    post_data = self._extract_post_from_element(element, forum_url, query)
                    if post_data:
                        found_posts.append(post_data)
                # Do not break immediately; gather from multiple selectors to broaden coverage

            # De-duplicate by URL
            unique = {}
            for p in found_posts:
                unique[p["url"]] = p
            found_posts = list(unique.values())

            # Filter posts that might be related to the query (basic keyword matching)
            relevant_posts = []
            query_lower = query.lower()

            for post in found_posts:
                title_lower = post.get('title', '').lower()
                body_lower = post.get('body', '').lower()
                if not query_lower.strip():
                    relevant_posts.append(post)
                    continue
                if any(word in title_lower or word in body_lower for word in query_lower.split()):
                    relevant_posts.append(post)

            if not relevant_posts:
                self.logger.debug(f"No keyword matches found on homepage for {forum_url} using query '{query}'")
            posts = relevant_posts[:limit]

        except Exception as e:
            self.logger.error(f"Error scraping forum {forum_url}: {e}")

        return posts
    
    async def _detect_forum_type(self, forum_url: str) -> str:
        """Try to detect the forum type from the homepage."""
        try:
            response = self.http_client.get_sync(forum_url)
            if not response or response.status_code != 200:
                return "generic"
            
            content = response.text.lower()
            
            if "discourse" in content or "discourse-application" in content:
                return "discourse"
            elif "phpbb" in content or "powered by phpbb" in content:
                return "phpbb"
            elif "vbulletin" in content or "powered by vbulletin" in content:
                return "vbulletin"
            else:
                return "generic"
        
        except Exception:
            return "generic"
    
    async def _search_forum_specific(
        self,
        forum_url: str,
        query: str,
        limit: int,
        forum_type: str
    ) -> List[Dict[str, Any]]:
        """Search using forum-specific patterns."""
        posts = []
        
        try:
            pattern = self.forum_patterns.get(forum_type, {})
            if not pattern.get("search_url"):
                return []
            
            # Build search URL
            search_path = pattern["search_url"].format(query=query)
            search_url = urljoin(forum_url, search_path)
            
            # Fetch search results
            response = self.http_client.get_sync(search_url)
            if not response or response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract posts using forum-specific selectors
            post_elements = soup.select(pattern["post_selector"])[:limit]
            
            for post_elem in post_elements:
                post_data = self._extract_post_data(
                    post_elem, forum_url, pattern, forum_type
                )
                if post_data:
                    posts.append(post_data)
        
        except Exception as e:
            self.logger.warning(f"Forum-specific search failed for {forum_url}: {e}")
        
        return posts
    
    async def _search_forum_generic(
        self,
        forum_url: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generic forum search by crawling pages."""
        posts = []
        
        try:
            # Try common forum page patterns
            search_urls = [
                f"{forum_url}/search?q={query}",
                f"{forum_url}/search.php?keywords={query}",
                f"{forum_url}/?s={query}",
                forum_url  # Fallback to homepage
            ]
            
            for search_url in search_urls:
                try:
                    response = self.http_client.get_sync(search_url)
                    if response and response.status_code == 200:
                        page_posts = await self._extract_posts_from_page(
                            response.text, forum_url, query
                        )
                        posts.extend(page_posts)
                        
                        if len(posts) >= limit:
                            break
                
                except Exception:
                    continue
        
        except Exception as e:
            self.logger.warning(f"Generic forum search failed for {forum_url}: {e}")
        
        return posts[:limit]
    
    async def _extract_posts_from_page(
        self,
        html: str,
        base_url: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Extract posts from HTML page using generic patterns."""
        posts = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            pattern = self.forum_patterns["generic"]
            
            # Find potential post elements
            post_elements = soup.select(pattern["post_selector"])
            
            for post_elem in post_elements:
                # Check if post is relevant to query
                text_content = post_elem.get_text().lower()
                if query.lower() not in text_content:
                    continue
                
                post_data = self._extract_post_data(
                    post_elem, base_url, pattern, "generic"
                )
                if post_data:
                    posts.append(post_data)
        
        except Exception as e:
            self.logger.warning(f"Error extracting posts from page: {e}")
        
        return posts
    
    def _extract_post_data(
        self,
        post_elem,
        base_url: str,
        pattern: Dict[str, str],
        forum_type: str
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a post element."""
        try:
            # Extract title
            title_elem = post_elem.select_one(pattern.get("title_selector", ""))
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract content
            content_elem = post_elem.select_one(pattern.get("content_selector", ""))
            content = content_elem.get_text().strip() if content_elem else post_elem.get_text().strip()
            
            # Extract author
            author_elem = post_elem.select_one(pattern.get("author_selector", ""))
            author = author_elem.get_text().strip() if author_elem else ""
            
            # Extract date
            date_elem = post_elem.select_one(pattern.get("date_selector", ""))
            date_str = ""
            if date_elem:
                date_str = date_elem.get("datetime") or date_elem.get_text().strip()
            
            # Try to parse date
            post_date = self._parse_date(date_str)
            
            # Extract URL
            url = self._extract_post_url(post_elem, base_url)
            
            # Clean and validate content
            if not title and not content:
                return None
            
            return {
                "title": title[:500] if title else "Forum Post",
                "content": content[:2000] if content else "",
                "author": author[:100] if author else "",
                "date": post_date,
                "url": url,
                "forum_url": base_url,
                "forum_type": forum_type,
                "score": 0,  # Generic forums typically don't have scoring
                "replies": self._extract_reply_count(post_elem)
            }
        
        except Exception as e:
            self.logger.warning(f"Error extracting post data: {e}")
            return None
    
    def _extract_post_url(self, post_elem, base_url: str) -> str:
        """Extract post URL from element."""
        try:
            # Look for various link patterns
            link_elem = (
                post_elem.find('a', href=True) or
                post_elem.select_one('[href]') or
                post_elem.parent.find('a', href=True) if post_elem.parent else None
            )
            
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                return urljoin(base_url, href)
            
            return base_url
        
        except Exception:
            return base_url
    
    def _extract_reply_count(self, post_elem) -> int:
        """Extract reply count from post element."""
        try:
            text = post_elem.get_text()
            # Look for patterns like "5 replies", "replies: 3", etc.
            reply_patterns = [
                r'(\d+)\s*repl',
                r'repl[^:]*:\s*(\d+)',
                r'(\d+)\s*response',
                r'(\d+)\s*comment'
            ]
            
            for pattern in reply_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return 0
        except Exception:
            return 0
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from forum post."""
        if not date_str:
            return None
        
        try:
            # Common date patterns in forums
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # ISO date
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
                r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
                r'(\w+ \d{1,2}, \d{4})',  # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    from dateutil import parser
                    return parser.parse(match.group(1))
            
            # Try parsing the full string
            from dateutil import parser
            return parser.parse(date_str)
        
        except Exception:
            return None
    
    async def scrape_forum_page(
        self,
        forum_url: str,
        page_limit: int = 5
    ) -> pd.DataFrame:
        """
        Scrape posts from forum pages.
        
        Args:
            forum_url: Base forum URL
            page_limit: Maximum number of pages to scrape
            
        Returns:
            DataFrame with forum posts
        """
        all_posts = []
        
        try:
            for page in range(1, page_limit + 1):
                page_url = f"{forum_url}?page={page}"
                
                response = self.http_client.get_sync(page_url)
                if not response or response.status_code != 200:
                    break
                
                page_posts = await self._extract_posts_from_page(
                    response.text, forum_url, ""
                )
                
                if not page_posts:
                    break
                
                all_posts.extend(page_posts)
                
                # Add delay between pages
                await asyncio.sleep(2)
            
            self.logger.info(f"Scraped {len(all_posts)} posts from {forum_url}")
            return pd.DataFrame(all_posts)
        
        except Exception as e:
            self.logger.error(f"Error scraping forum pages: {e}")
            return pd.DataFrame()
    
    def _extract_post_from_element(
        self,
        element,
        forum_url: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Extract post data from a HTML element."""
        try:
            # Try to find title
            title_elem = element.select_one('a, h1, h2, h3, h4, .title')
            title = title_elem.get_text().strip() if title_elem else "Untitled Post"

            # Try to find link
            link_elem = element.select_one('a')
            url = link_elem.get('href') if link_elem else forum_url
            if url and not url.startswith('http'):
                url = urljoin(forum_url, url)

            # Try to find author
            author_elem = element.select_one('.author, .username, .user, [data-user]')
            author = author_elem.get_text().strip() if author_elem else "Unknown"

            # Try to find date
            date_elem = element.select_one('.date, .time, time, [datetime]')
            date_str = date_elem.get('datetime') or date_elem.get_text().strip() if date_elem else None
            date = self._parse_date(date_str) if date_str else datetime.now()

            # Get body/content
            body_elem = element.select_one('.content, .body, .text, p')
            body = body_elem.get_text().strip() if body_elem else title

            # Create post data
            post_data = {
                "source": "forums",
                "title": title,
                "body": body,
                "author": author,
                "date": date,
                "url": url,
                "score": 0,  # Forums don't typically have scores
                "forum_url": forum_url
            }

            return post_data

        except Exception as e:
            self.logger.warning(f"Error extracting post data: {e}")
            return None