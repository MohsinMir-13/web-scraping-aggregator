#!/usr/bin/env python3
"""
Quick demo of the Web Scraping Aggregator functionality.
"""
import asyncio
import json
from datetime import datetime

async def demo():
    """Run a quick demo of the scraping functionality."""
    
    print("🕷️ Web Scraping Aggregator - Quick Demo")
    print("=" * 50)
    
    try:
        # Import after ensuring we're in the right directory
        from core.orchestrator import orchestrator
        
        print("✅ Successfully imported orchestrator")
        
        # Check scraper status
        print("\n📊 Scraper Status:")
        status = orchestrator.get_scraper_status()
        for source, info in status.items():
            configured = info["configured"]
            status_icon = "✅" if configured else "⚠️ "
            status_text = "Configured" if configured else "Limited (no API keys)"
            print(f"   {status_icon} {info['name']}: {status_text}")
        
        # Test search suggestions
        print(f"\n💡 Search Suggestions for 'python web scraping':")
        suggestions = orchestrator.get_search_suggestions("python web scraping")
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"   {i}. {suggestion}")
        
        # Try a simple search (this may have limited results without API keys)
        print(f"\n🔍 Testing search functionality...")
        print("Note: This demo uses limited API access. For full functionality, set up API keys in .env file.")
        
        # Test Stack Overflow search (doesn't require API key)
        try:
            results_df, metadata = await orchestrator.search_single_source(
                source="stackoverflow",
                query="python requests",
                limit=5,
                days_back=7
            )
            
            if not results_df.empty:
                print(f"✅ Stack Overflow search successful: {len(results_df)} results")
                print(f"   Search time: {metadata.get('search_time_seconds', 0):.2f} seconds")
                
                # Show a sample result
                if len(results_df) > 0:
                    sample = results_df.iloc[0]
                    print(f"\n📝 Sample result:")
                    print(f"   Title: {sample.get('title', 'N/A')[:80]}...")
                    print(f"   Author: {sample.get('author', 'N/A')}")
                    print(f"   Score: {sample.get('score', 'N/A')}")
                    print(f"   URL: {sample.get('url', 'N/A')}")
            else:
                print("⚠️  No results returned (this is normal for the demo)")
        
        except Exception as e:
            print(f"⚠️  Search test failed: {e}")
            print("This is normal without proper API configuration.")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Set up API keys in .env file for full functionality")
        print(f"2. Run the Streamlit web app: python3 -m streamlit run streamlit_app.py")
        print(f"3. Or use the launch script: ./launch.sh")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project directory")
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(demo())