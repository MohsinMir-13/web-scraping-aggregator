"""
Data processing and normalization utilities.
"""
import pandas as pd
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dateutil import parser
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class DataNormalizer:
    """Normalizes data from different sources into a standard format."""
    
    def __init__(self):
        self.standard_fields = [
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
    
    def normalize_date(self, date_input: Union[str, datetime, int, float]) -> Optional[datetime]:
        """
        Normalize various date formats to datetime object.
        
        Args:
            date_input: Date in various formats
            
        Returns:
            Normalized datetime object or None
        """
        if date_input is None:
            return None
            
        try:
            if isinstance(date_input, datetime):
                return date_input.replace(tzinfo=timezone.utc) if date_input.tzinfo is None else date_input
            elif isinstance(date_input, (int, float)):
                # Assume Unix timestamp
                return datetime.fromtimestamp(date_input, tz=timezone.utc)
            elif isinstance(date_input, str):
                # Parse string date
                parsed_date = parser.parse(date_input)
                return parsed_date.replace(tzinfo=timezone.utc) if parsed_date.tzinfo is None else parsed_date
        except (ValueError, TypeError, parser.ParserError) as e:
            logger.warning(f"Failed to parse date '{date_input}': {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove HTML tags (basic cleanup)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        return text
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ""
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""
    
    def normalize_record(self, record: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize a single record to standard format.
        
        Args:
            record: Raw record from data source
            source: Source name (reddit, github, etc.)
            
        Returns:
            Normalized record
        """
        normalized = {}
        
        # Standard field mapping
        for field in self.standard_fields:
            normalized[field] = None
        
        # Set source
        normalized["source"] = source
        
        # Common field mappings
        title_fields = ["title", "subject", "name", "question_title"]
        body_fields = ["body", "content", "text", "description", "question_body", "selftext"]
        author_fields = ["author", "user", "username", "display_name", "owner"]
        date_fields = ["created_utc", "created_at", "date", "timestamp", "creation_date"]
        url_fields = ["url", "permalink", "link", "html_url"]
        score_fields = ["score", "ups", "upvotes", "votes", "points"]
        comments_fields = ["num_comments", "comments", "comment_count", "answer_count"]
        
        # Map fields
        normalized["title"] = self._get_first_available(record, title_fields)
        normalized["body"] = self._get_first_available(record, body_fields)
        normalized["author"] = self._get_first_available(record, author_fields)
        normalized["url"] = self._get_first_available(record, url_fields)
        normalized["score"] = self._get_first_available(record, score_fields, default=0)
        normalized["comments_count"] = self._get_first_available(record, comments_fields, default=0)
        
        # Normalize date
        date_value = self._get_first_available(record, date_fields)
        normalized["date"] = self.normalize_date(date_value)
        
        # Clean text fields
        if normalized["title"]:
            normalized["title"] = self.clean_text(normalized["title"])
        if normalized["body"]:
            normalized["body"] = self.clean_text(normalized["body"])
        
        # Extract tags if available
        tags = record.get("tags", [])
        if isinstance(tags, list):
            normalized["tags"] = tags
        elif isinstance(tags, str):
            normalized["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            normalized["tags"] = []
        
        return normalized
    
    def _get_first_available(self, record: Dict[str, Any], field_names: List[str], default: Any = None) -> Any:
        """Get the first available field value from a list of possible field names."""
        for field_name in field_names:
            if field_name in record and record[field_name] is not None:
                return record[field_name]
        return default
    
    def normalize_dataframe(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        Normalize a DataFrame to standard format.
        
        Args:
            df: Input DataFrame
            source: Source name
            
        Returns:
            Normalized DataFrame
        """
        if df.empty:
            return pd.DataFrame(columns=self.standard_fields)
        
        normalized_records = []
        for _, record in df.iterrows():
            normalized_record = self.normalize_record(record.to_dict(), source)
            normalized_records.append(normalized_record)
        
        return pd.DataFrame(normalized_records)

def merge_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge multiple normalized DataFrames.
    
    Args:
        dataframes: List of normalized DataFrames
        
    Returns:
        Merged DataFrame
    """
    if not dataframes:
        return pd.DataFrame()
    
    # Filter out empty DataFrames
    non_empty_dfs = [df for df in dataframes if not df.empty]
    
    if not non_empty_dfs:
        return pd.DataFrame()
    
    # Concatenate all DataFrames
    merged_df = pd.concat(non_empty_dfs, ignore_index=True)
    
    # Sort by date (newest first)
    if "date" in merged_df.columns:
        merged_df = merged_df.sort_values("date", ascending=False)
    
    # Reset index
    merged_df = merged_df.reset_index(drop=True)
    
    logger.info(f"Merged {len(non_empty_dfs)} DataFrames into {len(merged_df)} total records")
    
    return merged_df

def export_data(df: pd.DataFrame, format: str, filename: str) -> str:
    """
    Export DataFrame to specified format.
    
    Args:
        df: DataFrame to export
        format: Export format ('csv' or 'json')
        filename: Output filename
        
    Returns:
        Path to exported file
    """
    try:
        if format.lower() == 'csv':
            df.to_csv(filename, index=False, encoding='utf-8')
        elif format.lower() == 'json':
            df.to_json(filename, orient='records', indent=2, date_format='iso')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported {len(df)} records to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise