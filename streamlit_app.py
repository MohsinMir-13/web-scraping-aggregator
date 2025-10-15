"""
Streamlit web application for the Web Scraping Aggregator.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
import json
import io
from typing import Dict, List, Any

# Configure page
st.set_page_config(
    page_title="Web Scraping Aggregator",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import after page config
from core.orchestrator import orchestrator
from config.settings import DATA_SOURCES, SCRAPING_CONFIG
from utils.data_utils import export_data
from utils.logging_utils import get_logger

logger = get_logger(__name__)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #3b82f6;
        margin-bottom: 2rem;
    }
    
    .source-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #3b82f6;
    }
    
    .success-message {
        background-color: #d1fae5;
        color: #065f46;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    
    .error-message {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6, #1d4ed8);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = pd.DataFrame()
    if 'search_metadata' not in st.session_state:
        st.session_state.search_metadata = {}
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    if 'scraper_status' not in st.session_state:
        st.session_state.scraper_status = {}

def render_header():
    """Render the application header."""
    st.markdown('<div class="main-header">🕷️ Web Scraping Aggregator</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #6b7280; margin-bottom: 2rem;">
        Construction & Roofing Intelligence for Latvia - Search discussions from Reddit, GitHub, forums, and more
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the sidebar with search configuration."""
    st.sidebar.title("🔍 Search Configuration")
    
    # Get scraper status
    if not st.session_state.scraper_status:
        st.session_state.scraper_status = orchestrator.get_scraper_status()
    
    # Search query
    query = st.sidebar.text_input(
        "Search Query",
        value=st.session_state.last_query,
        placeholder="e.g., flat roof repair Latvia, metal roofing Riga...",
        help="Enter construction/roofing topics, materials, locations, or contractor questions"
    )
    
    # Data source selection
    st.sidebar.subheader("📊 Data Sources")
    selected_sources = []
    
    for source_key, source_name in DATA_SOURCES.items():
        status = st.session_state.scraper_status.get(source_key, {})
        configured = status.get("configured", False)
        
        # Create checkbox with status indicator
        col1, col2 = st.sidebar.columns([3, 1])
        
        with col1:
            if st.checkbox(source_name, key=f"source_{source_key}"):
                selected_sources.append(source_key)
        
        with col2:
            if configured:
                st.markdown("✅", help="Configured and ready")
            else:
                st.markdown("⚠️", help="Limited functionality (missing API keys)")
    
    # Search parameters
    st.sidebar.subheader("⚙️ Parameters")
    
    limit_per_source = st.sidebar.slider(
        "Results per source",
        min_value=10,
        max_value=SCRAPING_CONFIG.MAX_LIMIT,
        value=SCRAPING_CONFIG.DEFAULT_LIMIT,
        step=10,
        help="Maximum number of results to fetch from each source"
    )
    
    days_back = st.sidebar.slider(
        "Days to search back",
        min_value=1,
        max_value=SCRAPING_CONFIG.MAX_DAYS_BACK,
        value=SCRAPING_CONFIG.DEFAULT_DAYS_BACK,
        help="How many days back to search for content"
    )
    
    # Advanced options
    with st.sidebar.expander("🔧 Advanced Options"):
        st.write("**Reddit Options**")
        reddit_subreddits = st.text_input(
            "Specific subreddits (comma-separated)",
            placeholder="Construction,Roofing,HomeImprovement,latvia",
            help="Leave empty to search construction/roofing/Latvia subreddits"
        )
        
        reddit_sort = st.selectbox(
            "Reddit sort method",
            ["relevance", "hot", "new", "top"],
            help="How to sort Reddit results"
        )

        reddit_include_all = st.checkbox(
            "Include r/all (broader search)",
            value=True,
            help="When enabled, part of the limit is spent searching r/all first to reduce topic bias."
        )

        reddit_curated_only = st.checkbox(
            "Limit to curated construction subreddits only",
            value=False,
            help="If enabled, skips r/all and only searches construction/roofing/Latvia subreddits."
        )

        extra_curated = st.text_input(
            "Additional curated subreddits (extend internal list)",
            placeholder="architecture, DIY, Latvia",
            help="Optional: extend the construction/roofing focused subreddit list."
        )
        
        st.write("**GitHub Options**")
        github_repos = st.text_input(
            "Specific repositories (comma-separated)",
            placeholder="construction-tools,roofing-calc", 
            help="Format: owner/repo. Leave empty for global construction project search"
        )
        
        github_type = st.selectbox(
            "GitHub search type",
            ["issues", "repositories"],
            help="Type of GitHub content to search"
        )
        
        st.write("**Stack Overflow Options**")
        so_tags = st.text_input(
            "Stack Overflow tags (comma-separated)",
            placeholder="construction,cad,architecture,building",
            help="Filter by construction/architecture related tags"
        )
        
        st.write("**Forum Options**")
        forum_urls = st.text_area(
            "Forum URLs (one per line)",
            placeholder="https://www.contractortalk.com\nhttps://www.diychatroom.com",
            help="URLs of construction/roofing forums to search"
        )
    
    return {
        "query": query,
        "selected_sources": selected_sources,
        "limit_per_source": limit_per_source,
        "days_back": days_back,
        "source_params": {
            "reddit": {
                "subreddits": [s.strip() for s in reddit_subreddits.split(",") if s.strip()] if reddit_subreddits else None,
                "sort": reddit_sort,
                "include_all": reddit_include_all,
                "curated_only": reddit_curated_only,
                "extra_curated": [c.strip() for c in extra_curated.split(',') if c.strip()] if extra_curated else []
            },
            "github": {
                "repositories": [r.strip() for r in github_repos.split(",") if r.strip()] if github_repos else None,
                "search_type": github_type
            },
            "stackoverflow": {
                "tags": [t.strip() for t in so_tags.split(",") if t.strip()] if so_tags else None
            },
            "forums": {
                "forum_urls": [url.strip() for url in forum_urls.split("\n") if url.strip()] if forum_urls else None
            }
        }
    }

async def perform_search(search_config: Dict[str, Any]) -> bool:
    """Perform the search operation."""
    query = search_config["query"]
    selected_sources = search_config["selected_sources"]
    
    if not query.strip():
        st.error("Please enter a search query")
        return False
    
    if not selected_sources:
        st.error("Please select at least one data source")
        return False
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress: int, message: str):
        progress_bar.progress(progress)
        status_text.text(message)
    
    try:
        # Perform search
        results_df, metadata = await orchestrator.search_all_sources(
            query=query,
            selected_sources=selected_sources,
            limit_per_source=search_config["limit_per_source"],
            days_back=search_config["days_back"],
            source_params=search_config["source_params"],
            progress_callback=update_progress
        )
        
        # Store results in session state
        st.session_state.search_results = results_df
        st.session_state.search_metadata = metadata
        st.session_state.last_query = query
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        return True
    
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Search failed: {str(e)}")
        logger.error(f"Search error: {e}")
        return False

def render_search_results():
    """Render search results and analytics."""
    if st.session_state.search_results.empty:
        st.info("No search results to display. Please perform a search first.")
        return
    
    df = st.session_state.search_results
    metadata = st.session_state.search_metadata
    
    st.subheader(f"📋 Search Results for '{metadata.get('query', 'Unknown')}'")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#3b82f6;">Total Results</h3>
            <h2 style="margin:0.5rem 0 0 0;">{len(df)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        sources_count = df['source'].nunique() if 'source' in df.columns else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#10b981;">Sources</h3>
            <h2 style="margin:0.5rem 0 0 0;">{sources_count}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        search_time = metadata.get('search_time_seconds', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#f59e0b;">Search Time</h3>
            <h2 style="margin:0.5rem 0 0 0;">{search_time}s</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if 'score' in df.columns and not df['score'].isna().all():
            clean_scores = pd.to_numeric(df['score'], errors='coerce').dropna()
            avg_score = clean_scores.mean() if len(clean_scores) > 0 else 0
        else:
            avg_score = 0
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#8b5cf6;">Avg Score</h3>
            <h2 style="margin:0.5rem 0 0 0;">{avg_score:.1f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Source breakdown
    st.subheader("📊 Results by Source")
    
    if 'source' in df.columns:
        source_counts = df['source'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create bar chart
            fig = px.bar(
                x=source_counts.index,
                y=source_counts.values,
                title="Results by Data Source",
                labels={'x': 'Data Source', 'y': 'Number of Results'},
                color=source_counts.values,
                color_continuous_scale='viridis'
            )
            fig.update_layout(
                xaxis_title="Data Source",
                yaxis_title="Number of Results",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Source details
            for source in source_counts.index:
                source_metadata = metadata.get('source_results', {}).get(source, {})
                success = source_metadata.get('success', False)
                count = source_metadata.get('count', 0)
                search_time = source_metadata.get('search_time_seconds', 0)
                
                status_icon = "✅" if success else "❌"
                source_name = DATA_SOURCES.get(source, source.title())
                
                st.markdown(f"""
                <div class="source-card">
                    <strong>{status_icon} {source_name}</strong><br>
                    Results: {count}<br>
                    Time: {search_time:.1f}s
                </div>
                """, unsafe_allow_html=True)
    
    # Filters
    st.subheader("🔍 Filter Results")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        if 'source' in df.columns:
            source_filter = st.multiselect(
                "Filter by source",
                options=df['source'].unique(),
                default=df['source'].unique()
            )
        else:
            source_filter = None
    
    with filter_col2:
        if 'score' in df.columns and not df['score'].isna().all():
            # Clean the score column - remove NaN and ensure numeric values
            clean_scores = pd.to_numeric(df['score'], errors='coerce').dropna()
            if len(clean_scores) > 0:
                min_val = int(clean_scores.min())
                max_val = int(clean_scores.max())
                # Ensure min_value is less than max_value for slider
                if min_val < max_val:
                    min_score = st.slider(
                        "Minimum score",
                        min_value=min_val,
                        max_value=max_val,
                        value=min_val
                    )
                else:
                    # If all scores are the same, show info and set filter to that value
                    st.info(f"All posts have the same score: {min_val}")
                    min_score = min_val
            else:
                min_score = None
        else:
            min_score = None
    
    with filter_col3:
        keyword_filter = st.text_input(
            "Filter by keyword",
            placeholder="Enter keyword to filter title/content"
        )
    
    # Apply filters
    filtered_df = orchestrator.filter_results(
        df,
        source_filter=source_filter,
        min_score=min_score,
        keyword_filter=keyword_filter
    )
    
    if len(filtered_df) < len(df):
        st.info(f"Showing {len(filtered_df)} of {len(df)} results after filtering")
    
    # Results table
    st.subheader("📋 Detailed Results")
    
    if not filtered_df.empty:
        # Configure display columns
        display_columns = ['source', 'title', 'author', 'date', 'score', 'url']
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        
        # Format the dataframe for display
        display_df = filtered_df[available_columns].copy()
        
        # Truncate long titles
        if 'title' in display_df.columns:
            display_df['title'] = display_df['title'].str[:100] + '...'
        
        # Format dates
        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Make URLs clickable
        if 'url' in display_df.columns:
            # Let LinkColumn handle the URL display
            pass
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("Link", display_text="🔗 Open"),
                "score": st.column_config.NumberColumn("Score", format="%d"),
                "source": st.column_config.TextColumn("Source"),
                "title": st.column_config.TextColumn("Title"),
                "author": st.column_config.TextColumn("Author"),
                "date": st.column_config.TextColumn("Date")
            }
        )
        
        # Export options
        st.subheader("💾 Export Data")
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            if st.button("📄 Download CSV", use_container_width=True):
                csv_buffer = io.StringIO()
                filtered_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="Click to download CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with export_col2:
            if st.button("📋 Download JSON", use_container_width=True):
                json_data = filtered_df.to_json(orient='records', indent=2, date_format='iso')
                st.download_button(
                    label="Click to download JSON",
                    data=json_data,
                    file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    else:
        st.warning("No results match the current filters.")

def render_analytics():
    """Render analytics and visualizations."""
    if st.session_state.search_results.empty:
        st.info("No data available for analytics. Please perform a search first.")
        return
    
    df = st.session_state.search_results
    
    st.subheader("📈 Analytics & Insights")
    
    # Time series analysis
    if 'date' in df.columns and not df['date'].isna().all():
        st.subheader("📅 Posts Over Time")
        
        # Convert dates and create time series
        df_with_dates = df.dropna(subset=['date']).copy()
        df_with_dates['date'] = pd.to_datetime(df_with_dates['date'])
        df_with_dates['date_only'] = df_with_dates['date'].dt.date
        
        # Group by date and source
        daily_counts = df_with_dates.groupby(['date_only', 'source']).size().reset_index(name='count')
        
        if not daily_counts.empty:
            fig = px.line(
                daily_counts,
                x='date_only',
                y='count',
                color='source',
                title='Posts per Day by Source',
                labels={'date_only': 'Date', 'count': 'Number of Posts', 'source': 'Source'}
            )
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Posts",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Top authors
    if 'author' in df.columns and not df['author'].isna().all():
        st.subheader("👥 Top Contributors")
        
        author_counts = df['author'].value_counts().head(10)
        
        if not author_counts.empty:
            fig = px.bar(
                x=author_counts.index,
                y=author_counts.values,
                title="Top 10 Contributors",
                labels={'x': 'Author', 'y': 'Number of Posts'},
                color=author_counts.values,
                color_continuous_scale='plasma'
            )
            fig.update_layout(
                xaxis_title="Author",
                yaxis_title="Number of Posts",
                showlegend=False
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Score distribution
    if 'score' in df.columns and not df['score'].isna().all():
        # Clean the score data for visualization
        clean_scores = pd.to_numeric(df['score'], errors='coerce').dropna()
        if len(clean_scores) > 0:
            st.subheader("⭐ Score Distribution")
            
            # Create a temporary dataframe with clean scores
            score_df = pd.DataFrame({'score': clean_scores})
            
            fig = px.histogram(
                score_df,
                x='score',
                nbins=20,
                title='Distribution of Post Scores',
                labels={'score': 'Score', 'count': 'Number of Posts'}
            )
            fig.update_layout(
                xaxis_title="Score",
                yaxis_title="Number of Posts"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Word cloud-like analysis (top terms)
    st.subheader("🔤 Popular Terms")
    
    if 'title' in df.columns:
        # Simple term frequency analysis
        all_titles = ' '.join(df['title'].dropna().astype(str))
        words = all_titles.lower().split()
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        word_counts = {}
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in stop_words:
                word_counts[clean_word] = word_counts.get(clean_word, 0) + 1
        
        if word_counts:
            top_words = dict(sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20])
            
            fig = px.bar(
                x=list(top_words.keys()),
                y=list(top_words.values()),
                title="Top 20 Terms in Titles",
                labels={'x': 'Term', 'y': 'Frequency'},
                color=list(top_words.values()),
                color_continuous_scale='viridis'
            )
            fig.update_layout(
                xaxis_title="Term",
                yaxis_title="Frequency",
                showlegend=False
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

def main():
    """Main application function."""
    initialize_session_state()
    render_header()
    
    # Main layout
    search_config = render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search", "📊 Results", "📈 Analytics"])
    
    with tab1:
        st.subheader("🚀 Start Your Search")
        
        # Search button
        if st.button("🔍 Search", use_container_width=True, type="primary"):
            with st.spinner("Searching across data sources..."):
                # Use existing running loop if present; Streamlit may manage one internally
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule the coroutine and wait via asyncio.run_coroutine_threadsafe
                        fut = asyncio.run_coroutine_threadsafe(perform_search(search_config), loop)
                        success = fut.result()
                    else:
                        success = loop.run_until_complete(perform_search(search_config))
                except RuntimeError:
                    # Fallback: no loop set, use asyncio.run
                    success = asyncio.run(perform_search(search_config))

                if success:
                    st.success("Search completed successfully!")
                    st.balloons()
        
        # Search suggestions
        if search_config["query"]:
            st.subheader("💡 Search Suggestions")
            suggestions = orchestrator.get_search_suggestions(search_config["query"])
            if suggestions:
                suggestion_cols = st.columns(min(len(suggestions), 3))
                for i, suggestion in enumerate(suggestions[:6]):
                    with suggestion_cols[i % 3]:
                        if st.button(f"💡 {suggestion}", key=f"suggestion_{i}"):
                            st.rerun()
        
        # Scraper status
        st.subheader("🔧 Scraper Status")
        status = st.session_state.scraper_status
        
        status_cols = st.columns(len(DATA_SOURCES))
        for i, (source_key, source_name) in enumerate(DATA_SOURCES.items()):
            with status_cols[i]:
                source_status = status.get(source_key, {})
                configured = source_status.get("configured", False)
                
                if configured:
                    st.success(f"✅ {source_name}")
                    st.caption("Fully configured")
                else:
                    st.warning(f"⚠️ {source_name}")
                    st.caption("Limited functionality")
    
    with tab2:
        render_search_results()
    
    with tab3:
        render_analytics()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; padding: 1rem;">
        🕷️ Web Scraping Aggregator | Built with Streamlit | 
        <a href="https://github.com" target="_blank">View on GitHub</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()