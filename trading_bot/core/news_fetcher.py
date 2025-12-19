
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from core.logger import setup_logger
import random

logger = setup_logger("NewsFetcher", "logs/news_fetcher.log")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]

class NewsFetcher:
    @staticmethod
    def get_news(symbol):
        """
        Try yfinance first. If empty or failed, fallback to Google News RSS.
        Returns list of headlines.
        """
        headlines = []
        
        # 1. Try Yahoo Finance
        try:
            # Ticker.news usage
            ticker = yf.Ticker(symbol)
            yf_news = ticker.news
            if yf_news:
                headlines = [n['title'] for n in yf_news if 'title' in n]
                if headlines:
                    return headlines[:5]
        except Exception as e:
            logger.warning(f"Yahoo News failed for {symbol}: {e}")

        # 2. Fallback: Google News RSS
        if not headlines:
            headlines = NewsFetcher.fetch_google_news(symbol)
            if headlines:
                logger.info(f"Using Google News fallback for {symbol} ({len(headlines)} items)")
        
        return headlines[:5]

    @staticmethod
    def fetch_google_news(symbol):
        try:
            # Search query: "{symbol} stock news"
            url = f"https://news.google.com/rss/search?q={symbol}+stock+news&hl=en-US&gl=US&ceid=US:en"
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            
            # Simple XML Parse
            root = ET.fromstring(resp.content)
            headlines = []
            
            # Iterate items in channel
            for item in root.findall('./channel/item'):
                title = item.find('title').text
                if title:
                    headlines.append(title)
            
            return headlines
        except Exception as e:
            logger.error(f"Google News RSS failed for {symbol}: {e}")
            return []
