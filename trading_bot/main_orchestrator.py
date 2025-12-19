import asyncio
import logging
import time
from datetime import datetime, timedelta
import yfinance as yf

import pytz

# Boardroom Modules
from core.market_data import MarketData
from agents.manager_otto import Otto
import database as db
from core.config import CRYPTO_TICKERS, TICKERS, BATCH_SIZE
from core.trade_executor import TradeExecutor
from core.market_scanner import MarketScanner
from technical_analyst import TechnicalAnalyst
from core.logger import setup_logger

# Configure Logging
logger = setup_logger("Orchestrator", "logs/orchestrator.log")

class Orchestrator:
    def __init__(self):
        self.otto = Otto()
        self.last_conference = datetime.min
        self.current_budget = {'stock_agent': 0.5, 'crypto_agent': 0.5} # Default
        self.trade_executor = TradeExecutor()
        self.market_scanner = MarketScanner(self.trade_executor)
        self.spy_analyst = TechnicalAnalyst("SPY")
        self.current_market_bias = "NEUTRAL"

    def is_trading_hours(self):
        """Returns True if current time is within Trading Hours (08:30 - 17:00 ET) Mon-Fri"""
        # Simple implementation assuming server time is UTC or correctly set. 
        # Ideally use pytz, but sticking to standard lib for minimal deps if possible, 
        # or just offset. Assuming VM is UTC.
        # ET is UTC-5 (Standard) or UTC-4 (Daylight). Let's use specific ET offset if possible.
        # For simplicity and robustness on cloud VM (often UTC):
        
        # ET is UTC-5 (Standard) or UTC-4 (Daylight).
        # robustness using pytz
        
        utc_now = datetime.now(pytz.utc)
        et_now = utc_now.astimezone(pytz.timezone('US/Eastern')) 
        
        if et_now.weekday() > 4: return False # Weekend
        
        # 08:30 to 17:00
        start = et_now.replace(hour=8, minute=30, second=0, microsecond=0)
        end = et_now.replace(hour=17, minute=0, second=0, microsecond=0)
        
        return start <= et_now <= end

    async def morning_conference(self):
        """Run the daily strategy meeting with Otto (Once per day at 09:00 ET)"""
        if not self.is_trading_hours(): return

        # Check if we already ran today (in ET)
        utc_now = datetime.now(pytz.utc)
        et_now = utc_now.astimezone(pytz.timezone('US/Eastern'))
        
        # safely handle initial state
        if self.last_conference == datetime.min:
            last_conf_et = datetime.min
        else:
            # last_conference is stored as UTC (naive or aware? lets ensure consistency)
            # If it was naive UTC before, we should treat it as such
            if self.last_conference.tzinfo is None:
                 self.last_conference = pytz.utc.localize(self.last_conference)
            
            last_conf_et = self.last_conference.astimezone(pytz.timezone('US/Eastern'))
        
        if last_conf_et != datetime.min and last_conf_et.date() == et_now.date():
            return # Already ran today
            
        # Run only if it's past 08:55 AM (close to open)
        if et_now.hour < 8 or (et_now.hour == 8 and et_now.minute < 55):
            return

        logger.info("👔 === Starting Morning Conference ===")
        
        # 1. Gather Intelligence
        brief = MarketData.get_market_brief()
        
        # 2. Get Morning Momentum (NEW)
        # Scan watchlist for top movers
        watchlist = TICKERS
        movers_report = await self.market_scanner.get_movers(watchlist)
        
        # 3. Ask Otto
        daily_pnl = 0.0 
        allocation = self.otto.morning_briefing(daily_pnl, brief, self.current_market_bias)
        
        # 4. Enact Policy
        self.current_budget = allocation
        db.set_config("budget_allocation", allocation)
        self.last_conference = datetime.now(pytz.utc) # Store as Aware UTC
        
        # Log Decision
        msg = (
            f"📢 *Morning Intelligence Report (ANALYSIS ONLY)*\n"
            f"📅 {et_now.strftime('%Y-%m-%d')}\n\n"
            f"**🚀 Momentum:**\n{movers_report}\n\n"
            f"**🧠 Strategy:**\n"
            f"Stocks: {allocation['stock_agent']*100:.0f}%\n"
            f"Crypto: {allocation['crypto_agent']*100:.0f}%"
        )
        self.trade_executor.send_telegram_alert(msg)
        logger.info("=== Conference Adjourned ===")

    async def get_target_tickers(self):
        """Filter tickers based on Otto's budget"""
        # Base List (S&P 500 + Watchlist)
        sp500 = self.market_scanner.get_sp500_tickers()
        watchlist = TICKERS
        all_tickers = list(set(sp500 + watchlist))
        
        # Logic: If Crypto Budget < 0.1 (10%), CUT crypto completely
        if self.current_budget['crypto_agent'] < 0.1:
            logger.warning(f"🚫 Otto banned Crypto (Budget {self.current_budget['crypto_agent']:.2f}). Removing crypto tickers.")
            filtered = [t for t in all_tickers if t not in CRYPTO_TICKERS]
            return filtered
        
        # ADD Crypto Tickers explicitly if budget allows (Fix for blind spot)
        # Ensure they are in the list if not already
        for crypto in CRYPTO_TICKERS:
            if crypto not in all_tickers:
                all_tickers.append(crypto)

        return all_tickers

    async def check_market_panic(self):
        """Checks if SPY or BTC dropped > 2% in the last hour"""
        try:
            # Quick check using yfinance
            tickers = ['SPY', 'BTC-USD']
            data = await asyncio.to_thread(yf.download, tickers, period="1d", interval="1h", progress=False)
            
            panic_detected = False
            reasons = []

            for sym in tickers:
                try:
                    # Get last 2 candles
                    if len(tickers) > 1:
                        closes = data['Close'][sym].dropna()
                    else:
                        closes = data['Close'].dropna()
                        
                    if len(closes) < 2: continue
                    
                    last_price = closes.iloc[-1]
                    prev_price = closes.iloc[-2]
                    
                    drop_pct = ((last_price - prev_price) / prev_price) * 100
                    
                    # PANIC THRESHOLD: -2.0% in 1 hour
                    if drop_pct < -2.0:
                        panic_detected = True
                        reasons.append(f"{sym} crashed {drop_pct:.2f}%")
                except Exception as e: 
                    continue

            if panic_detected:
                logger.warning(f"🚨 PANIC DETECTED: {', '.join(reasons)}")
                return True
            return False
        except Exception as e:
            logger.error(f"Panic check failed: {e}")
            return False

    async def heartbeat(self):
        while True:
            # Respect Trading Hours (Silence at night)
            if not self.is_trading_hours():
                # Sleep longer if outside hours (check every hour)
                await asyncio.sleep(3600)
                continue

            stats = self.trade_executor.trader.get_summary()
            bias_emoji = "✅" if self.current_market_bias == 'BUY' else ("🛑" if self.current_market_bias == 'SELL' else "⚖️")
            
            msg = (
                f"💓 *Hourly STATUS REPORT*\n"
                f"**Bias:** {self.current_market_bias} {bias_emoji}\n"
                f"**Cash:** ${stats['cash']:.2f}\n"
                f"**Pos:** {stats['open_positions']}\n"
                f"**Trades:** {stats['realized_trades']}\n"
                f"**Active:** SHOP.TO, HUT.TO, NVDA..."
            )
            self.trade_executor.send_telegram_alert(msg)
            await asyncio.sleep(3600)

    async def run_loop(self):
        logger.info("🚀 Boardroom Orchestrator Started")
        
        # Start Heartbeat
        asyncio.create_task(self.heartbeat())

        while True:
            try:
                # 0. PANIC CHECK (The Emergency Interrupter)
                if await self.check_market_panic():
                    logger.warning("🚨 EMERGENCY BOARD MEETING TRIGGERED!")
                    # Force Otto to re-evaluate immediately
                    self.last_conference = datetime.min 
                    await self.morning_conference()

                # 1. Strategy Check (Normal Schedule)
                await self.morning_conference()
                
                # 2. Market Scan
                # Monitor Portfolio First
                await self.trade_executor.monitor_portfolio()
                
                if not self.is_trading_hours():
                    logger.info("🌙 After Hours: Scanning paused.")
                else:
                    # Update Market Bias (SPY Check) - Only during market hours
                    bias_result = await self.spy_analyst.analyze()
                    self.current_market_bias = bias_result['signal']
                    db.set_config("market_bias", self.current_market_bias)
                    
                    # Determine Scope
                    targets = await self.get_target_tickers()
                    
                    # If budget is 0 for everything, sleep and skip
                    if not targets:
                        logger.info("💤 Otto has set all budgets to 0. Sleeping...")
                    else:
                        logger.info(f"🎯 Target Scope: {len(targets)} tickers (Otto's Orders)")
                        
                        # Batch Scan
                        for i in range(0, len(targets), BATCH_SIZE):
                            batch = targets[i:i + BATCH_SIZE]
                            await self.market_scanner.scan_batch(batch, self.current_market_bias)
                            await asyncio.sleep(1)
                
                # Sleep
                logger.info("💤 Resting for 5 minutes...")
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Orchestrator Loop Error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    orchestrator = Orchestrator()
    asyncio.run(orchestrator.run_loop())
