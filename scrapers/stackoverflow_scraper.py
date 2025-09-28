"""
Stack Overflow scraper using the Stack Exchange API.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import requests
from config.settings import API_CONFIG
from scrapers.base_scraper import BaseScraper
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class StackOverflowScraper(BaseScraper):
    """Scraper for Stack Overflow using the Stack Exchange API."""
    
    def __init__(self):
        super().__init__("stackoverflow")
        self.base_url = "https://api.stackexchange.com/2.3"
        self.site = "stackoverflow"
        
    def validate_config(self) -> bool:
        """Validate Stack Exchange API configuration."""
        return True  # Stack Exchange API works without key (with rate limits)
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        search_type: str = "questions",
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Search Stack Overflow for questions, answers, or users.
        
        Args:
            query: Search query
            limit: Maximum number of results
            days_back: Days to search back
            search_type: Type of search ('questions', 'answers')
            tags: Filter by specific tags
            
        Returns:
            DataFrame with Stack Overflow results
        """
        self.logger.info(f"Searching Stack Overflow {search_type} for '{query}' (limit={limit}, days_back={days_back})")
        
        try:
            start_date, end_date = self.get_date_range(days_back)
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            if search_type == "questions":
                results = await self._search_questions(
                    query, limit, start_timestamp, end_timestamp, tags
                )
            elif search_type == "answers":
                results = await self._search_answers(
                    query, limit, start_timestamp, end_timestamp
                )
            else:
                self.logger.error(f"Unsupported search type: {search_type}")
                return pd.DataFrame()
            
            self.logger.info(f"Found {len(results)} Stack Overflow {search_type}")
            return pd.DataFrame(results)
        
        except Exception as e:
            self.logger.error(f"Stack Overflow search failed: {e}")
            return pd.DataFrame()
    
    async def _search_questions(
        self,
        query: str,
        limit: int,
        start_timestamp: int,
        end_timestamp: int,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for questions on Stack Overflow."""
        questions = []
        
        try:
            # Build API parameters
            params = {
                "order": "desc",
                "sort": "relevance",
                "q": query,  # Use q parameter to search in title and body
                "site": self.site,
                "pagesize": min(limit, 100),  # API max is 100
                "fromdate": start_timestamp,
                "todate": end_timestamp,
                "filter": "default"  # Use default filter instead of withbody
            }
            
            if tags:
                params["tagged"] = ";".join(tags)
            
            if API_CONFIG.STACKEXCHANGE_KEY:
                params["key"] = API_CONFIG.STACKEXCHANGE_KEY
            
            # Make API request
            response = requests.get(f"{self.base_url}/search", params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "items" in data:
                for item in data["items"]:
                    question_data = self._extract_question_data(item)
                    questions.append(question_data)
            
            # Handle pagination if needed
            page = 2
            while len(questions) < limit and data.get("has_more", False) and page <= 10:
                params["page"] = page
                response = requests.get(f"{self.base_url}/search", params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if "items" in data:
                    for item in data["items"]:
                        if len(questions) >= limit:
                            break
                        question_data = self._extract_question_data(item)
                        questions.append(question_data)
                
                page += 1
        
        except Exception as e:
            self.logger.error(f"Error searching Stack Overflow questions: {e}")
        
        return questions
    
    async def _search_answers(
        self,
        query: str,
        limit: int,
        start_timestamp: int,
        end_timestamp: int
    ) -> List[Dict[str, Any]]:
        """Search for answers on Stack Overflow."""
        answers = []
        
        try:
            # First, search for questions to get question IDs
            questions = await self._search_questions(
                query, limit, start_timestamp, end_timestamp
            )
            
            # Then get answers for those questions
            question_ids = [q.get("question_id") for q in questions if q.get("question_id")]
            
            if question_ids:
                # Get answers for the questions
                params = {
                    "order": "desc",
                    "sort": "votes",
                    "site": self.site,
                    "pagesize": min(limit, 100),
                    "filter": "withbody"
                }
                
                if API_CONFIG.STACKEXCHANGE_KEY:
                    params["key"] = API_CONFIG.STACKEXCHANGE_KEY
                
                # Process in batches (API limits)
                batch_size = 30
                for i in range(0, len(question_ids), batch_size):
                    batch_ids = question_ids[i:i + batch_size]
                    ids_str = ";".join(map(str, batch_ids))
                    
                    response = requests.get(
                        f"{self.base_url}/questions/{ids_str}/answers",
                        params=params,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    if "items" in data:
                        for item in data["items"]:
                            if len(answers) >= limit:
                                break
                            answer_data = self._extract_answer_data(item)
                            answers.append(answer_data)
        
        except Exception as e:
            self.logger.error(f"Error searching Stack Overflow answers: {e}")
        
        return answers
    
    def _extract_question_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from a Stack Overflow question."""
        try:
            return {
                "question_id": item.get("question_id"),
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "author": item.get("owner", {}).get("display_name", ""),
                "creation_date": item.get("creation_date"),
                "last_activity_date": item.get("last_activity_date"),
                "score": item.get("score", 0),
                "view_count": item.get("view_count", 0),
                "answer_count": item.get("answer_count", 0),
                "comment_count": item.get("comment_count", 0),
                "favorite_count": item.get("favorite_count", 0),
                "url": item.get("link", ""),
                "tags": item.get("tags", []),
                "is_answered": item.get("is_answered", False),
                "accepted_answer_id": item.get("accepted_answer_id"),
                "question_timeline_url": item.get("question_timeline_url", ""),
                "question_comments_url": item.get("question_comments_url", "")
            }
        except Exception as e:
            self.logger.warning(f"Error extracting question data: {e}")
            return {}
    
    def _extract_answer_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from a Stack Overflow answer."""
        try:
            return {
                "answer_id": item.get("answer_id"),
                "question_id": item.get("question_id"),
                "title": f"Answer to Question {item.get('question_id', '')}",
                "body": item.get("body", ""),
                "author": item.get("owner", {}).get("display_name", ""),
                "creation_date": item.get("creation_date"),
                "last_activity_date": item.get("last_activity_date"),
                "score": item.get("score", 0),
                "comment_count": item.get("comment_count", 0),
                "url": item.get("link", ""),
                "is_accepted": item.get("is_accepted", False),
                "community_owned_date": item.get("community_owned_date")
            }
        except Exception as e:
            self.logger.warning(f"Error extracting answer data: {e}")
            return {}
    
    async def get_questions_by_tags(
        self,
        tags: List[str],
        limit: int = 50,
        sort: str = "votes"
    ) -> pd.DataFrame:
        """
        Get questions filtered by specific tags.
        
        Args:
            tags: List of tags to filter by
            limit: Number of questions to fetch
            sort: Sort method ('votes', 'activity', 'creation', 'relevance')
            
        Returns:
            DataFrame with tagged questions
        """
        try:
            params = {
                "order": "desc",
                "sort": sort,
                "tagged": ";".join(tags),
                "site": self.site,
                "pagesize": min(limit, 100),
                "filter": "withbody"
            }
            
            if API_CONFIG.STACKEXCHANGE_KEY:
                params["key"] = API_CONFIG.STACKEXCHANGE_KEY
            
            response = requests.get(f"{self.base_url}/questions", params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            questions = []
            
            if "items" in data:
                for item in data["items"]:
                    question_data = self._extract_question_data(item)
                    questions.append(question_data)
            
            self.logger.info(f"Retrieved {len(questions)} questions with tags: {', '.join(tags)}")
            return pd.DataFrame(questions)
        
        except Exception as e:
            self.logger.error(f"Error fetching questions by tags: {e}")
            return pd.DataFrame()