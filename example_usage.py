"""
Example script demonstrating programmatic usage of the scraping orchestrator.
"""
import asyncio
import json
from datetime import datetime

from core.orchestrator import orchestrator
from utils.data_utils import export_data
from utils.logging_utils import setup_logger

# Setup logging
logger = setup_logger("example_script", log_file="logs/example.log")

async def example_search():
    """Example of how to use the orchestrator programmatically."""
    
    # Example 1: Simple search across all sources
    logger.info("Starting example search...")
    
    query = "python web scraping"
    sources = ["reddit", "github", "stackoverflow"]
    
    try:
        results_df, metadata = await orchestrator.search_all_sources(
            query=query,
            selected_sources=sources,
            limit_per_source=20,
            days_back=7,
            source_params={
                "reddit": {
                    "subreddits": ["python", "webscraping"],
                    "sort": "relevance"
                },
                "github": {
                    "search_type": "issues"
                },
                "stackoverflow": {
                    "tags": ["python", "web-scraping"]
                }
            }
        )
        
        logger.info(f"Search completed. Found {len(results_df)} total results.")
        
        # Print metadata
        print("\n=== Search Metadata ===")
        print(json.dumps(metadata, indent=2, default=str))
        
        # Display some results
        if not results_df.empty:
            print(f"\n=== Sample Results (showing first 5) ===")
            display_columns = ['source', 'title', 'author', 'score', 'date']
            available_columns = [col for col in display_columns if col in results_df.columns]
            
            sample_df = results_df[available_columns].head()
            print(sample_df.to_string(index=False))
            
            # Export results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"exports/example_results_{timestamp}.csv"
            json_file = f"exports/example_results_{timestamp}.json"
            
            # Create exports directory
            import os
            os.makedirs("exports", exist_ok=True)
            
            export_data(results_df, "csv", csv_file)
            export_data(results_df, "json", json_file)
            
            logger.info(f"Results exported to {csv_file} and {json_file}")
        
        # Example 2: Search individual sources
        print(f"\n=== Individual Source Search ===")
        
        reddit_df, reddit_meta = await orchestrator.search_single_source(
            source="reddit",
            query="machine learning",
            limit=10,
            subreddits=["MachineLearning", "artificial"]
        )
        
        print(f"Reddit search: {len(reddit_df)} results")
        print(f"Search time: {reddit_meta.get('search_time_seconds', 0):.2f}s")
        
        # Example 3: Filter results
        if not results_df.empty:
            print(f"\n=== Filtering Example ===")
            
            # Filter for high-score posts from the last 3 days
            from datetime import timedelta
            recent_date = datetime.now() - timedelta(days=3)
            
            filtered_df = orchestrator.filter_results(
                results_df,
                source_filter=["reddit", "stackoverflow"],
                min_score=5,
                keyword_filter="API"
            )
            
            print(f"Filtered results: {len(filtered_df)} (from {len(results_df)} original)")
        
    except Exception as e:
        logger.error(f"Example search failed: {e}")
        raise

async def check_scraper_status():
    """Check the status of all scrapers."""
    print("\n=== Scraper Status ===")
    
    status = orchestrator.get_scraper_status()
    
    for source, info in status.items():
        status_icon = "✅" if info["configured"] else "⚠️ "
        print(f"{status_icon} {info['name']}: {'Configured' if info['configured'] else 'Limited (no API key)'}")

async def main():
    """Main example function."""
    print("🕷️ Web Scraping Aggregator - Example Usage")
    print("=" * 50)
    
    # Check scraper status
    await check_scraper_status()
    
    # Run example search
    await example_search()
    
    print("\n✅ Example completed successfully!")
    print("Check the 'exports' directory for exported results.")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())