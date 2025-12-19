
import logging
import asyncio
import yfinance as yf
import pandas as pd
import requests
import database as db
from technical_analyst import TechnicalAnalyst
from core.config import INDEX_URL, DEFAULT_SENTIMENT, DEFAULT_VOL_MULT, STRICT_SENTIMENT, STRICT_VOL_MULT, CRYPTO_TICKERS
from core.sentiment import SentimentAnalyzer
from core.trade_executor import TradeExecutor
from core.news_fetcher import NewsFetcher
from core.logger import setup_logger

logger = setup_logger("MarketScanner", "logs/market_scanner.log")

class MarketScanner:
    def __init__(self, trade_executor: TradeExecutor):
        self.trade_executor = trade_executor
        self.sentiment_analyzer = SentimentAnalyzer()

    def get_sp500_tickers(self):
        try:
            # TODO: Convert to async with aiohttp?
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(INDEX_URL, headers=headers)
            r.raise_for_status()
            tables = pd.read_html(r.text)
            df = tables[0]
            tickers = df['Symbol'].tolist()
            return [t.replace('.', '-') for t in tickers]
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500: {e}")
            return []



    async def get_movers(self, tickers):
        """
        Scans values for Top Gainers/Losers/Volume for Morning Report.
        Returns a formatted string.
        """
        try:
            if not tickers: return "No tickers to scan."

            # Fetch Data (Price + Volume)
            data = await asyncio.to_thread(yf.download, tickers, period="2d", group_by='ticker', progress=False, threads=True)
            
            movers = []
            for symbol in tickers:
                try:
                    if len(tickers) == 1: hist = data
                    else: hist = data[symbol] if symbol in data else None
                    
                    if hist is None or hist.empty or len(hist) < 2: continue
                    
                    # Calculate Change
                    close = hist['Close']
                    vol = hist['Volume']

                    prev_close = float(close.iloc[-2])
                    curr_close = float(close.iloc[-1])
                    curr_vol = int(vol.iloc[-1])
                    
                    pct_change = ((curr_close - prev_close) / prev_close) * 100
                    
                    movers.append({
                        'symbol': symbol,
                        'price': curr_close,
                        'change': pct_change,
                        'volume': curr_vol
                    })
                except Exception: continue
            
            if not movers: return "No movers data available."

            # Sort by absolute change (Volatility)
            movers.sort(key=lambda x: x['change'], reverse=True)
            top_3 = movers[:3]
            
            report = []
            for m in top_3:
                emoji = "🟢" if m['change'] > 0 else "🔴"
                report.append(f"{emoji} {m['symbol']} ${m['price']:.2f} ({m['change']:+.2f}%)")
            
            return "\n".join(report)
        except Exception as e:
            logger.error(f"Failed to get movers: {e}")
            return "Error retrieving movers."



    def get_symbol_news(self, symbol):
        return NewsFetcher.get_news(symbol)

    def get_fundamentals(self, symbol):
        # 1. Check Cache
        cached_pe = db.get_fundamental(symbol)
        if cached_pe is not None:
            return cached_pe

        # 2. Fetch API
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            pe = info.get('forwardPE') or info.get('trailingPE')
            
            # 3. Save Cache
            if pe is not None:
                db.set_fundamental(symbol, pe)
                
            return pe
        except Exception:
            return None

    async def process_candidate(self, symbol, curr_vol, avg_vol, sent_thresh, market_bias):
        try:
            # V2 ARCHITECTURE: Parallel Analysis (Async)
            # We launch ALL checks simultaneously to reduce latency
            
            # 1. Define Tasks
            news_task = asyncio.to_thread(self.get_symbol_news, symbol)
            fund_task = asyncio.to_thread(self.get_fundamentals, symbol)
            
            # Initialize Technical Analyst
            stock_analyst = TechnicalAnalyst(symbol)
            tech_task = stock_analyst.analyze()
            
            # TODO: Add Sector Check Task here (e.g. check BTC if symbol is crypto)
            
            # 2. Await All concurrently
            headlines, pe_ratio, ta_result = await asyncio.gather(news_task, fund_task, tech_task)
            
            # 3. Calculate Scores
            volume_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
            sentiment_score = self.sentiment_analyzer.analyze(headlines)
            
            meta = {
                'curr_vol': curr_vol,
                'avg_vol': avg_vol,
                'volume_ratio': volume_ratio,
                'sentiment_score': sentiment_score,
                'pe_ratio': pe_ratio,
                'headlines': headlines,
                'market_bias': market_bias
            }

            # 4. "Gatekeeper" Logic (Aggregated Decision)
            
            # Gate 1: Sentiment
            if sentiment_score < sent_thresh:
                await self.trade_executor.log_rejection(symbol, None, f'Low sentiment ({sentiment_score:.2f} < {sent_thresh})', meta)
                return 

            # Gate 2: Fundamentals (Relaxed for Swing & Crypto)
            is_crypto = symbol in CRYPTO_TICKERS or '-USD' in symbol

            if not is_crypto:
                # P/E limit raised to 150 to catch Tech high-flyers (NVDA, TSLA)
                # EXCEPTION: Allow High P/E if Strong Technicals OR Extreme Volume
                if pe_ratio and pe_ratio > 150:
                    is_momentum = (ta_result['signal'] == 'STRONG_BUY') or (volume_ratio > 3.0)
                    
                    if not is_momentum:
                        await self.trade_executor.log_rejection(symbol, None, f'Extreme Valuation (P/E {pe_ratio:.1f} > 150) & No Momentum', meta)
                        return
                    else:
                         logger.info(f"🚀 MOMENTUM EXCEPTION: {symbol} passed with P/E {pe_ratio} due to Strong Technicals/Volume.")
            
            # Gate 3: Technicals
            if ta_result['signal'] == 'SELL':
                 # Even with great news, do not catch a falling knife
                 await self.trade_executor.log_rejection(symbol, 'SELL', 'Technical signal is SELL (Downtrend/Overbought)', {**meta, 'price': ta_result.get('latest_price')})
                 return 
            
            # Gate 4: Sector Correlation (Basic Implementation)
            # If Crypto stock, check if Bitcoin is crashing
            # This is a placeholder for refined logic
            if symbol in ['COIN', 'MSTR', 'MARA', 'RIOT', 'HUT.TO', 'BITF.TO']:
                # TODO: formatting check for sector health
                pass

            logger.info(f"✅ CANDIDATE PASSED: {symbol} (Sent: {sentiment_score:.2f}, Vol: {volume_ratio:.1f}x)")
            
            # Execute Trade
            result = await self.trade_executor.execute_trade_logic(symbol, ta_result, meta)
            return result

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None

    async def scan_batch(self, tickers, market_bias="NEUTRAL"):
        if not tickers: return
        
        sent_thresh = DEFAULT_SENTIMENT
        vol_thresh = DEFAULT_VOL_MULT
        
        if market_bias == 'SELL':
            # In bear market, require higher standards
            sent_thresh = STRICT_SENTIMENT
            vol_thresh = STRICT_VOL_MULT

        logger.info(f"Scanning Watchlist ({len(tickers)})...")
        try:
            data = await asyncio.to_thread(yf.download, tickers, period="5d", interval="1d", group_by='ticker', progress=False, threads=True)
            
            candidates = []
            for symbol in tickers:
                try:
                    if len(tickers) == 1: hist = data
                    else: hist = data[symbol] if symbol in data else None
                    
                    if hist is None or hist.empty or 'Volume' not in hist: continue
                    
                    volumes = hist['Volume'].dropna()
                    if len(volumes) < 2: continue
                    
                    current_vol = volumes.iloc[-1]
                    avg_vol = volumes.mean()
                    
                    if avg_vol > 0 and current_vol > (avg_vol * vol_thresh):
                        candidates.append((symbol, current_vol, avg_vol))
                except Exception: continue

            logger.info(f"Batch: {len(candidates)} movers.")
            
            # LOGGING FIX: Record heartbeats even if 0 movers
            if not candidates:
                 # Log a "SCAN" event so Decision Log isn't empty
                 await asyncio.to_thread(db.log_analysis,
                    symbol="MARKET",
                    volume_ratio=0.0,
                    sentiment_score=0.0,
                    pe_ratio=0.0,
                    technical_signal="NEUTRAL",
                    action_taken="SCAN",
                    reason=f"Scanned {len(tickers)} tickers. No volume spikes detected.",
                    price=0.0
                 )

            if candidates:
                # Filter out active positions
                positions = self.trade_executor.trader.positions
                valid_candidates = [c for c in candidates if c[0] not in positions]
                
                tasks = []
                for symbol, curr_vol, avg_vol in valid_candidates:
                    tasks.append(self.process_candidate(symbol, curr_vol, avg_vol, sent_thresh, market_bias))
                
                if tasks:
                    results = await asyncio.gather(*tasks)
                    
                    # Process Results for Notification Batching
                    skipped = [r for r in results if r and r.get('status') == 'SKIPPED']
                    
                    if skipped:
                        # Send Consolidated Summary
                        skipped_symbols = [s['symbol'] for s in skipped]
                        msg = (
                            f"⚠️ **Batch Scan Summary:**\n"
                            f"Found {len(skipped)} valid buy signals but skipped due to funds:\n"
                            f"{', '.join(skipped_symbols)}\n\n"
                            f"*Action:* Deposit funds or adjust allocation/P&L settings."
                        )
                        # Spam Control: Do not alert for skipped trades (insufficient funds)
                        # self.trade_executor.send_telegram_alert(msg)
                        logger.info(f"Skipped alert for {len(skipped)} symbols due to funds.")

        except Exception as e:
            logger.error(f"Batch failed: {e}")
