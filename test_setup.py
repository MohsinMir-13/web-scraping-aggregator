"""
Simple test to verify the application setup and basic functionality.
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """Test that all modules can be imported successfully."""
    print("🧪 Testing imports...")
    
    try:
        from config.settings import SCRAPING_CONFIG, API_CONFIG, DATA_SOURCES
        print("✅ Config module imported successfully")
        
        from utils.logging_utils import setup_logger
        from utils.data_utils import DataNormalizer
        from utils.http_utils import HTTPClient
        print("✅ Utils modules imported successfully")
        
        from scrapers import RedditScraper, GitHubScraper, StackOverflowScraper, ForumScraper
        print("✅ Scraper modules imported successfully")
        
        from core.orchestrator import orchestrator
        print("✅ Core orchestrator imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def test_scrapers():
    """Test scraper initialization."""
    print("\n🧪 Testing scraper initialization...")
    
    try:
        from scrapers import RedditScraper, GitHubScraper, StackOverflowScraper, ForumScraper
        
        # Test scraper initialization
        reddit = RedditScraper()
        github = GitHubScraper()
        stackoverflow = StackOverflowScraper()
        forums = ForumScraper()
        
        print("✅ All scrapers initialized successfully")
        
        # Test scraper status
        scrapers = [
            ("Reddit", reddit),
            ("GitHub", github), 
            ("Stack Overflow", stackoverflow),
            ("Forums", forums)
        ]
        
        for name, scraper in scrapers:
            configured = scraper.validate_config()
            status = "✅ Configured" if configured else "⚠️  Limited (no API key)"
            print(f"   {name}: {status}")
        
        return True
    except Exception as e:
        print(f"❌ Scraper test error: {e}")
        return False

async def test_orchestrator():
    """Test orchestrator functionality."""
    print("\n🧪 Testing orchestrator...")
    
    try:
        from core.orchestrator import orchestrator
        
        # Test scraper status
        status = orchestrator.get_scraper_status()
        print(f"✅ Orchestrator loaded with {len(status)} scrapers")
        
        # Test search suggestions
        suggestions = orchestrator.get_search_suggestions("python programming")
        print(f"✅ Generated {len(suggestions)} search suggestions")
        
        return True
    except Exception as e:
        print(f"❌ Orchestrator test error: {e}")
        return False

async def test_data_processing():
    """Test data processing utilities."""
    print("\n🧪 Testing data processing...")
    
    try:
        from utils.data_utils import DataNormalizer, merge_dataframes
        import pandas as pd
        
        # Test normalizer
        normalizer = DataNormalizer()
        
        # Test with sample data
        sample_data = {
            "title": "Test Post",
            "body": "This is a test post",
            "author": "test_user",
            "created_utc": 1695900000,
            "score": 10,
            "num_comments": 5
        }
        
        normalized = normalizer.normalize_record(sample_data, "test")
        print("✅ Data normalization working")
        
        # Test DataFrame processing
        df = pd.DataFrame([normalized])
        merged = merge_dataframes([df])
        print("✅ DataFrame processing working")
        
        return True
    except Exception as e:
        print(f"❌ Data processing test error: {e}")
        return False

async def test_streamlit_imports():
    """Test Streamlit and visualization dependencies."""
    print("\n🧪 Testing Streamlit dependencies...")
    
    try:
        import streamlit as st
        print("✅ Streamlit imported successfully")
        
        import pandas as pd
        print("✅ Pandas imported successfully")
        
        try:
            import plotly.express as px
            import plotly.graph_objects as go
            print("✅ Plotly imported successfully")
        except ImportError:
            print("⚠️  Plotly not available - install with: pip install plotly")
        
        return True
    except ImportError as e:
        print(f"❌ Streamlit dependencies error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🕷️ Web Scraping Aggregator - System Test")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Scraper Tests", test_scrapers),
        ("Orchestrator Tests", test_orchestrator),
        ("Data Processing Tests", test_data_processing),
        ("Streamlit Dependencies", test_streamlit_imports)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The application is ready to use.")
        print("\nTo start the Streamlit app, run:")
        print("   streamlit run streamlit_app.py")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the installation.")
        if passed > 0:
            print("The application may still work with limited functionality.")

if __name__ == "__main__":
    asyncio.run(main())