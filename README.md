# 🕷️ Web Scraping Aggregator

A comprehensive web scraping and aggregation tool with a modern Streamlit interface that collects discussions and posts from multiple online sources including Reddit, GitHub Issues/Discussions, Stack Overflow, and generic forums.

## ✨ Features

- **Multi-Source Scraping**: Collect data from Reddit, GitHub, Stack Overflow, and generic forums
- **Modern Web Interface**: Clean, responsive Streamlit dashboard with interactive visualizations
- **Concurrent Processing**: Fast, asynchronous scraping across multiple sources
- **Data Normalization**: Standardized output format across all sources
- **Advanced Filtering**: Filter results by source, date, score, and keywords
- **Export Functionality**: Download results in CSV or JSON format
- **Real-time Analytics**: Interactive charts and insights
- **Rate Limiting**: Respects robots.txt and implements intelligent rate limiting
- **Configurable Sources**: Support for API keys and advanced source-specific options

## 🏗️ Architecture

```
web-scraping-aggregator/
├── scrapers/                 # Individual scraper modules
│   ├── base_scraper.py      # Abstract base class
│   ├── reddit_scraper.py    # Reddit API integration
│   ├── github_scraper.py    # GitHub API integration
│   ├── stackoverflow_scraper.py  # Stack Exchange API
│   └── forum_scraper.py     # Generic HTML forum scraper
├── core/                    # Core orchestration logic
│   └── orchestrator.py      # Main coordination engine
├── utils/                   # Utility functions
│   ├── data_utils.py        # Data processing and normalization
│   ├── http_utils.py        # HTTP client with rate limiting
│   └── logging_utils.py     # Logging configuration
├── config/                  # Configuration management
│   └── settings.py          # Application settings
├── streamlit_app.py         # Main Streamlit application
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd webs-craping
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys (Optional but recommended)**
   ```bash
   cp .env.example .env
   # Edit .env file with your API credentials
   ```

5. **Install Playwright browsers (for JavaScript-heavy sites)**
   ```bash
   playwright install
   ```

### Running the Application

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## 🔧 Configuration

### API Keys (Optional but Recommended)

While the application works without API keys, having them provides better rate limits and access to more features:

#### Reddit API
1. Go to https://www.reddit.com/prefs/apps
2. Create a new application (select "script" type)
3. Add your `client_id` and `client_secret` to `.env`

#### GitHub API
1. Go to https://github.com/settings/tokens
2. Generate a new personal access token
3. Add the token to `.env`

#### Stack Exchange API
1. Go to https://stackapps.com/apps/oauth/register
2. Register your application
3. Add your API key to `.env`

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=WebScrapingAggregator/1.0

# GitHub API
GITHUB_TOKEN=your_github_token

# Stack Exchange API
STACKEXCHANGE_KEY=your_stackexchange_key
```

## 🎯 Usage

### Basic Search

1. **Enter your search query** in the sidebar
2. **Select data sources** you want to search
3. **Configure parameters** (results per source, date range)
4. **Click Search** to start scraping

### Advanced Options

- **Reddit**: Specify subreddits, sort methods
- **GitHub**: Target specific repositories, choose between issues/repositories
- **Stack Overflow**: Filter by programming tags
- **Forums**: Provide specific forum URLs to scrape

### Results and Analytics

- **Results Tab**: View, filter, and export your data
- **Analytics Tab**: Interactive visualizations and insights
- **Export**: Download results as CSV or JSON

## 🔍 Supported Sources

### Reddit
- **API**: Official Reddit API via PRAW
- **Features**: Subreddit-specific search, various sorting options
- **Rate Limits**: 60 requests per minute (with API key)

### GitHub
- **API**: GitHub REST API v4
- **Features**: Issues, discussions, repositories search
- **Rate Limits**: 5000 requests per hour (with token)

### Stack Overflow
- **API**: Stack Exchange API v2.3
- **Features**: Questions, answers, tag-based filtering
- **Rate Limits**: 300 requests per day (10,000 with key)

### Generic Forums
- **Method**: HTML scraping with BeautifulSoup
- **Supported**: Discourse, phpBB, vBulletin, and generic forums
- **Features**: Auto-detection of forum types, robots.txt compliance

## 📊 Data Schema

All scraped data is normalized to a common schema:

```python
{
    "source": "reddit|github|stackoverflow|forums",
    "title": "Post/Issue title",
    "body": "Content/description", 
    "author": "Username/author",
    "date": "ISO timestamp",
    "url": "Direct link to post",
    "score": "Upvotes/score (numeric)",
    "comments_count": "Number of comments/replies",
    "tags": ["list", "of", "tags"]
}
```

## 🛠️ Development

### Project Structure

- **Modular Design**: Each data source has its own scraper module
- **Async Support**: Built with asyncio for concurrent scraping
- **Error Handling**: Comprehensive error handling and logging
- **Rate Limiting**: Intelligent rate limiting per source
- **Extensible**: Easy to add new data sources

### Adding New Data Sources

1. Create a new scraper class inheriting from `BaseScraper`
2. Implement the `search()` method
3. Add the scraper to the orchestrator
4. Update the configuration

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## 🔒 Privacy and Ethics

- **Robots.txt Compliance**: Respects robots.txt files
- **Rate Limiting**: Implements conservative rate limits
- **Terms of Service**: Users responsible for API ToS compliance
- **Data Privacy**: No persistent storage of scraped data by default

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**"Import errors when running"**
- Make sure you've installed all dependencies: `pip install -r requirements.txt`
- Try reinstalling: `pip install --upgrade -r requirements.txt`

**"No results from Reddit/GitHub"**
- Check your API credentials in `.env`
- Verify your API keys are valid and have proper permissions

**"Playwright browser not found"**
- Install browsers: `playwright install`

**"Rate limit errors"**
- Add API keys to increase rate limits
- Reduce the number of results per source
- Increase delays in configuration

**"Forum scraping not working"**
- Check if the forum allows scraping (robots.txt)
- Verify the forum URL is accessible
- Some forums may require JavaScript - these need Playwright

### Performance Tips

- Use API keys for better rate limits
- Start with smaller result sets for testing
- Use specific subreddits/repositories instead of global search
- Enable concurrent processing (default)

## 🔮 Future Enhancements

- [ ] Database persistence (MongoDB/PostgreSQL)
- [ ] User authentication and saved searches
- [ ] Email notifications for new results
- [ ] More data sources (Twitter, LinkedIn, etc.)
- [ ] Machine learning for content classification
- [ ] Docker containerization
- [ ] RESTful API endpoint
- [ ] Advanced text analytics and sentiment analysis

## 📞 Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Include error logs and configuration details

---

**Built with ❤️ using Python, Streamlit, and modern web scraping techniques.**