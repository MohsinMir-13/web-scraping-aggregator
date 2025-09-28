"""
GitHub scraper using the GitHub REST API.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import requests
from github import Github
from config.settings import API_CONFIG
from scrapers.base_scraper import BaseScraper
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class GitHubScraper(BaseScraper):
    """Scraper for GitHub Issues and Discussions using PyGithub."""
    
    def __init__(self):
        super().__init__("github")
        self.github = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GitHub API client."""
        try:
            if API_CONFIG.GITHUB_TOKEN:
                self.github = Github(API_CONFIG.GITHUB_TOKEN)
                self.logger.info("GitHub API client initialized successfully")
            else:
                # Use unauthenticated client (lower rate limits)
                self.github = Github()
                self.logger.warning("GitHub API token not found. Using unauthenticated access (limited rate limits).")
        except Exception as e:
            self.logger.error(f"Failed to initialize GitHub client: {e}")
            self.github = None
    
    def validate_config(self) -> bool:
        """Validate GitHub API configuration."""
        return self.github is not None
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        days_back: int = 30,
        repositories: Optional[List[str]] = None,
        search_type: str = "issues",
        **kwargs
    ) -> pd.DataFrame:
        """
        Search GitHub for issues, discussions, or repositories.
        
        Args:
            query: Search query
            limit: Maximum number of results
            days_back: Days to search back
            repositories: Specific repositories to search (format: "owner/repo")
            search_type: Type of search ('issues', 'repositories', 'discussions')
            
        Returns:
            DataFrame with GitHub results
        """
        if not self.github:
            self.logger.error("GitHub client not initialized")
            return pd.DataFrame()
        
        self.logger.info(f"Searching GitHub {search_type} for '{query}' (limit={limit}, days_back={days_back})")
        
        try:
            results = []
            start_date, end_date = self.get_date_range(days_back)
            
            if repositories:
                # Search in specific repositories
                for repo_name in repositories:
                    try:
                        repo_results = await self._search_repository(
                            repo_name, query, limit // len(repositories), start_date, search_type
                        )
                        results.extend(repo_results)
                    except Exception as e:
                        self.logger.warning(f"Error searching repository {repo_name}: {e}")
            else:
                # Global search
                if search_type == "issues":
                    results = await self._search_global_issues(query, limit, start_date)
                elif search_type == "repositories":
                    results = await self._search_repositories(query, limit)
                elif search_type == "discussions":
                    # Note: GitHub Discussions API is more limited
                    self.logger.warning("Global discussions search not fully supported. Consider specifying repositories.")
            
            self.logger.info(f"Found {len(results)} GitHub {search_type}")
            return pd.DataFrame(results)
        
        except Exception as e:
            self.logger.error(f"GitHub search failed: {e}")
            return pd.DataFrame()
    
    async def _search_global_issues(
        self,
        query: str,
        limit: int,
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Search for issues globally across GitHub."""
        issues = []
        
        try:
            # Build search query with date filter
            date_filter = start_date.strftime("%Y-%m-%d")
            search_query = f"{query} created:>={date_filter}"
            
            search_results = self.github.search_issues(
                query=search_query,
                sort="created",
                order="desc"
            )
            
            count = 0
            for issue in search_results:
                if count >= limit:
                    break
                
                issue_data = self._extract_issue_data(issue)
                issues.append(issue_data)
                count += 1
        
        except Exception as e:
            self.logger.error(f"Error searching global issues: {e}")
        
        return issues
    
    async def _search_repositories(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search for repositories."""
        repos = []
        
        try:
            search_results = self.github.search_repositories(
                query=query,
                sort="stars",
                order="desc"
            )
            
            count = 0
            for repo in search_results:
                if count >= limit:
                    break
                
                repo_data = self._extract_repository_data(repo)
                repos.append(repo_data)
                count += 1
        
        except Exception as e:
            self.logger.error(f"Error searching repositories: {e}")
        
        return repos
    
    async def _search_repository(
        self,
        repo_name: str,
        query: str,
        limit: int,
        start_date: datetime,
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Search within a specific repository."""
        results = []
        
        try:
            repo = self.github.get_repo(repo_name)
            
            if search_type == "issues":
                issues = repo.get_issues(
                    state="all",
                    since=start_date,
                    sort="created",
                    direction="desc"
                )
                
                count = 0
                for issue in issues:
                    if count >= limit:
                        break
                    
                    # Filter by query in title or body
                    if (query.lower() in issue.title.lower() or 
                        (issue.body and query.lower() in issue.body.lower())):
                        issue_data = self._extract_issue_data(issue)
                        results.append(issue_data)
                        count += 1
            
            elif search_type == "discussions":
                # Note: Discussions API requires GraphQL, which is more complex
                # For now, we'll skip discussions in repository-specific search
                self.logger.warning(f"Discussions search not implemented for {repo_name}")
        
        except Exception as e:
            self.logger.warning(f"Error searching repository {repo_name}: {e}")
        
        return results
    
    def _extract_issue_data(self, issue) -> Dict[str, Any]:
        """Extract data from a GitHub issue."""
        try:
            return {
                "title": issue.title,
                "body": issue.body or "",
                "author": issue.user.login if issue.user else "",
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "state": issue.state,
                "comments": issue.comments,
                "url": issue.html_url,
                "repository": issue.repository.full_name if hasattr(issue, 'repository') else "",
                "number": issue.number,
                "labels": [label.name for label in issue.labels],
                "assignees": [assignee.login for assignee in issue.assignees],
                "milestone": issue.milestone.title if issue.milestone else "",
                "is_pull_request": issue.pull_request is not None,
                "reactions": getattr(issue, "reactions", {}).get("total_count", 0)
            }
        except Exception as e:
            self.logger.warning(f"Error extracting issue data: {e}")
            return {}
    
    def _extract_repository_data(self, repo) -> Dict[str, Any]:
        """Extract data from a GitHub repository."""
        try:
            return {
                "title": repo.name,
                "body": repo.description or "",
                "author": repo.owner.login if repo.owner else "",
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "url": repo.html_url,
                "language": repo.language or "",
                "topics": repo.get_topics(),
                "license": repo.license.name if repo.license else "",
                "size": repo.size,
                "open_issues": repo.open_issues_count,
                "default_branch": repo.default_branch,
                "archived": repo.archived,
                "disabled": repo.disabled
            }
        except Exception as e:
            self.logger.warning(f"Error extracting repository data: {e}")
            return {}
    
    async def get_repository_issues(
        self,
        repo_name: str,
        limit: int = 50,
        state: str = "open"
    ) -> pd.DataFrame:
        """
        Get issues from a specific repository.
        
        Args:
            repo_name: Repository name (format: "owner/repo")
            limit: Number of issues to fetch
            state: Issue state ('open', 'closed', 'all')
            
        Returns:
            DataFrame with repository issues
        """
        if not self.github:
            return pd.DataFrame()
        
        try:
            repo = self.github.get_repo(repo_name)
            issues = []
            
            repo_issues = repo.get_issues(
                state=state,
                sort="created",
                direction="desc"
            )
            
            count = 0
            for issue in repo_issues:
                if count >= limit:
                    break
                
                issue_data = self._extract_issue_data(issue)
                issues.append(issue_data)
                count += 1
            
            self.logger.info(f"Retrieved {len(issues)} issues from {repo_name}")
            return pd.DataFrame(issues)
        
        except Exception as e:
            self.logger.error(f"Error fetching repository issues: {e}")
            return pd.DataFrame()