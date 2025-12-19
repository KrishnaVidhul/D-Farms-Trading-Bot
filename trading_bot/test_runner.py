import os
import asyncio
import logging
import requests
from technical_analyst import TechnicalAnalyst 

# Setup simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRunner")

# Mock Telegram sender
def send_telegram_alert(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if not token or not chat_id:
        logger.error("❌ Telegram credentials missing in env!")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("✅ Telegram Alert Sent Successfully!")
        else:
            logger.error(f"❌ Telegram Alert Failed: {r.text}")
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")

async def run_test():
    logger.info("🧪 Starting V2 Bot Self-Test...")
    
    # 1. Test Technical Analyst (SPY)
    logger.info("Step 1: Testing Technical Analyst on SPY...")
    try:
        spy = TechnicalAnalyst("SPY")
        result = await spy.analyze()
        logger.info(f"✅ SPY Analysis Result: {result}")
        
        bias = result['signal']
        rsi = result.get('rsi', 0)
        price = result['latest_price']
        
    except Exception as e:
        logger.error(f"❌ Technical Analyst Failed: {e}")
        return

    # 2. Test Telegram
    logger.info("Step 2: Sending Test Alert...")
    msg = (
        f"🧪 *TEST ALERT - DIAGNOSTICS*\n"
        f"The V2 Bot is operational.\n\n"
        f"**SPY Check:**\n"
        f"Signal: {bias}\n"
        f"Price: ${price:.2f}\n"
        f"RSI: {rsi:.2f}\n"
        f"Time: {os.popen('date').read().strip()}"
    )
    send_telegram_alert(msg)
    
    logger.info("🧪 Test Complete.")

if __name__ == "__main__":
    asyncio.run(run_test())
