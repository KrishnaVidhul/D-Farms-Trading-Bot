import sys
import os
import yfinance as yf
import logging

# Ensure parent directory is in path to import database
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import database as db

logger = logging.getLogger("MarketData")

class MarketData:
    @staticmethod
    def get_current_price(symbol):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0

    @staticmethod
    def get_market_brief():
        """
        Fetches Top 3 headlines for SPY and BTC-USD.
        Cached for 1 hour in SQLite.
        """
        CACHE_KEY = "market_brief_v2"
        
        # 1. Check Cache
        cached = db.get_cache(CACHE_KEY)
        if cached:
            # Valid cache hit
            logger.info("🗞️ Using Cached Market Brief")
            return cached

        # If no cache or invalid, proceed to fetch
        logger.info("📰 Fetching Fresh Market Brief...")
        
        try:
            from core.news_fetcher import NewsFetcher
            import os
            from groq import Groq
            
            # Gather Raw Data
            spy_news = NewsFetcher.get_news("SPY")
            btc_news = NewsFetcher.get_news("BTC-USD")
            
            # Formatting Context
            raw_text = f"Market News (SPY):\n" + "\n".join(spy_news[:5]) + "\n\nCrypto News (BTC):\n" + "\n".join(btc_news[:3])
            
            # AI Summarization
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            prompt = (
                "You are an elite hedge fund analyst. unexpected huge volatility is expected today. "
                "Summarize these headlines into a high-level Morning Briefing for a trader. "
                "Format as follows:\n"
                "### 🌍 Market Pulse\n"
                "- [Bullet 1: Key Driver]\n"
                "- [Bullet 2: Sentiment]\n\n"
                "### 🪙 Crypto Watch\n"
                "- [Bullet 1]\n\n"
                "**Bias:** [BULLISH/BEARISH/NEUTRAL] because [Reason]"
                "\n\nRules: Keep it concise. No URLs. value only."
                f"\n\nData:\n{raw_text}"
            )
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
            )
            
            final_summary = chat_completion.choices[0].message.content
            
            # Save Cache (60 mins)
            db.set_cache(CACHE_KEY, final_summary, ttl_minutes=60)
            
            return final_summary

        except Exception as e:
            logger.error(f"Failed to generate AI brief: {e}")
            return "⚠️ **Briefing Unavailable:** AI Summarization failed. Check logs."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(MarketData.get_market_brief())
    print(f"BTC Price: {MarketData.get_current_price('BTC-USD')}")
