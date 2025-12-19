
import asyncio
import logging
import sys
import os

# Ensure we can import core components
sys.path.append(os.getcwd())

from core.market_scanner import MarketScanner
from core.trade_executor import TradeExecutor
import core.market_scanner

# PATCH: Lower volume threshold to ensure we find "movers" for testing
core.market_scanner.DEFAULT_VOL_MULT = 0.0
core.market_scanner.STRICT_VOL_MULT = 0.0


# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VerifyLogic")

async def run_verification():
    logger.info("🚀 Starting Full Logic Verification (High Balance Simulation)")
    
    # 1. Initialize Components
    executor = TradeExecutor()
    scanner = MarketScanner(executor)
    
    # 2. Mock High Balance to bypass "Insufficient Funds"
    # Overwrite the paper trader's balance temporally for this script
    executor.trader.balance = 100000.0 
    logger.info(f"💰 Mocked Balance: ${executor.trader.balance:,.2f}")
    
    # 3. Define Test Watchlist (High Probability Movers)
    test_tickers = ['NVDA', 'AMD', 'PLTR', 'TSLA', 'COIN']
    logger.info(f"📋 Scanning Targets: {test_tickers}")
    
    # 4. Run Batch Scan
    # We pass 'NEUTRAL' bias to allow standard buys
    await scanner.scan_batch(test_tickers, market_bias="NEUTRAL")
    
    # 5. Report
    print("\n--- VERIFICATION SUMMARY ---")
    print(f"Final Mock Balance: ${executor.trader.balance:,.2f}")
    if executor.trader.balance < 100000.0:
        print("✅ SUCCESS: Trades were executed (Balance decreased).")
    else:
        print("⚠️ WARNING: No trades executed. Check logs for rejections.")

if __name__ == "__main__":
    asyncio.run(run_verification())
