# Web Scraping Aggregator - Production Deployment

runtime.txt (for Heroku):
python-3.11.9

Procfile (for Heroku):
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0

For Streamlit Cloud:
- Just push to GitHub and connect your repository
- Streamlit Cloud will automatically detect streamlit_app.py as the main file

For Railway/Render:
- Use the same Procfile format
- Set environment variables through their dashboard

For Vercel:
- Add vercel.json configuration file