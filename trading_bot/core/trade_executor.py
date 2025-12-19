
import logging
import asyncio
import database as db
from paper_trader import PaperTrader
from technical_analyst import TechnicalAnalyst
from core.config import TELEGRAM_TOKEN, CHAT_ID
from core.logger import setup_logger
import requests

logger = setup_logger("TradeExecutor", "logs/trade_executor.log")

class TradeExecutor:
    def __init__(self):
        self.trader = PaperTrader()

    def send_telegram_alert(self, message):
        try:
            if not TELEGRAM_TOKEN or not CHAT_ID:
                logger.warning("Telegram token or Chat ID missing. Alert skipped.")
                return
                
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    async def execute_trade_logic(self, symbol, analysis_result, meta_data):
        """
        Executes buy logic based on analysis result.
        meta_data should contain: volume_ratio, sentiment_score, pe_ratio, headlines
        """
        curr_vol = meta_data.get('curr_vol', 0)
        avg_vol = meta_data.get('avg_vol', 0)
        volume_ratio = meta_data.get('volume_ratio', 0)
        sentiment_score = meta_data.get('sentiment_score', 0)
        pe_ratio = meta_data.get('pe_ratio', 0)
        headlines = meta_data.get('headlines', [])
        market_bias = meta_data.get('market_bias', 'NEUTRAL')
        
        ta_result = analysis_result
        latest_price = ta_result['latest_price']

        # Log: Passed all checks - attempting buy
        db.log_analysis(symbol, volume_ratio, sentiment_score, pe_ratio, ta_result['signal'], 'BUY_SIGNAL', f"All checks passed. Confidence: {ta_result['confidence']}", latest_price)
        
        receipt = self.trader.buy(symbol, latest_price)
        
        paper_msg = ""
        if receipt:
            fee_pct = receipt['fee_rate'] * 100
            paper_msg = (
                f"\n📜 **BUY EXEC:**\n"
                f"Amt: {receipt['shares']} @ ${receipt['price']:.2f}\n"
                f"Fee: {fee_pct}%\n"
                f"**Break-Even:** ${receipt['break_even']:.2f}"
            )
            # Log: Successfully bought
            db.log_analysis(symbol, volume_ratio, sentiment_score, pe_ratio, ta_result['signal'], 'BOUGHT', f"Executed {receipt['shares']} shares", latest_price)
        else:
            paper_msg = "\n(Skipped: Insufficient Funds)"
            # Log: Wanted to buy but couldn't
            db.log_analysis(symbol, volume_ratio, sentiment_score, pe_ratio, ta_result['signal'], 'INSUFFICIENT_FUNDS', 'Not enough capital', latest_price)
        
        pe_str = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
        
        if receipt:
            header = f"🚀 *BUY EXEC: {symbol}*"
            status_msg = paper_msg
            log_msg = "TRIGGER: {symbol} (EXECUTED)"
        else:
            header = f"🔔 *BUY SIGNAL: {symbol}* (Manual)"
            status_msg = f"\n⚠️ **Paper Trade Skipped:** {paper_msg}\n*Action:* Manual Execution Suggested"
            log_msg = f"TRIGGER: {symbol} (SIGNAL ONLY - Funds)"

        msg = (
            f"{header}\n"
            f"**Signal:** {ta_result['signal']} ({ta_result['confidence']})\n"
            f"**Price:** ${latest_price:.2f}\n"
            f"**RSI:** {ta_result.get('rsi', 50.0):.1f}\n"
            f"**Sentiment:** {sentiment_score:.2f}\n"
            f"**Vol Spike:** {int(curr_vol):,} (Avg: {int(avg_vol):,})\n"
            f"{status_msg}\n"
            f"**News:**\n" + "\n".join([f"- {h}" for h in headlines])
        )
        
        logger.info(log_msg)
        self.send_telegram_alert(msg)
        
        if receipt:
            return {'status': 'EXECUTED', 'symbol': symbol, 'price': latest_price }
        else:
            return {'status': 'SIGNAL_SENT', 'symbol': symbol, 'reason': 'Insufficient Funds'}

    async def log_rejection(self, symbol, reason_code, reason_desc, meta_data):
        volume_ratio = meta_data.get('volume_ratio', 0)
        sentiment_score = meta_data.get('sentiment_score', 0)
        pe_ratio = meta_data.get('pe_ratio', 0)
        price = meta_data.get('price', None)
        
        logger.info(f"Skipping {symbol}: {reason_desc}")
        db.log_analysis(symbol, volume_ratio, sentiment_score, pe_ratio, reason_code, 'REJECTED', reason_desc, price)

    async def monitor_portfolio(self):
        positions = list(self.trader.positions.keys())
        if not positions:
            return

        logger.info(f"💼 Monitoring {len(positions)} held positions...")
        
        for symbol in positions:
            try:
                # 1. Get Current Price
                analyst = TechnicalAnalyst(symbol)
                result = await analyst.analyze()
                curr_price = result['latest_price']
                
                # 2. Portfolio Match
                pos = self.trader.positions[symbol]
                avg_price = pos['avg_price']
                entry_fee = pos['fee_rate'] # 0.0 or 0.015
                
                # 3. Calculate Hypothetical Net P&L (if sold now)
                # Sell Fee matches Buy Fee logic
                sell_fee = entry_fee 
                proceeds = (pos['shares'] * curr_price) * (1 - sell_fee)
                cost_basis = pos['cost_basis']
                pnl = proceeds - cost_basis
                pnl_percent_net = (pnl / cost_basis) * 100
                
                # 4. Strategy Targets (5-Day Sprint)
                # Universal Rule: Target +5% (Speed is key)
                tp_target = 5.0 
                
                # SL: Widen to -4.0% for Swing
                sl_price = avg_price * 0.96 
                price_drop_pct = ((curr_price - avg_price) / avg_price) * 100
                
                # Time Stop (The 5-Day Rule)
                from datetime import datetime
                entry_date = datetime.fromisoformat(pos['entry_date'])
                days_held = (datetime.now() - entry_date).days
                
                action = None
                reason = ""
                
                if pnl_percent_net >= tp_target:
                    action = 'SELL'
                    reason = f"🎯 Profit Target Hit (+{pnl_percent_net:.1f}% Net)"
                elif days_held >= 5:
                    # Time Stop: Force Sell if 5 days passed
                    if pnl_percent_net > -2.0:
                        action = 'SELL'
                        reason = f"⏳ 5-Day Sprint End (PnL: {pnl_percent_net:.1f}%)"
                    else:
                        # Holding a loser > -2%? Maybe cut it.
                        # For now, let SL handle deep losers, but Time Stop cuts stagnant ones.
                        pass
                elif curr_price < sl_price:
                    action = 'SELL'
                    reason = f"🛑 Stop Loss Hit (Dropped {price_drop_pct:.1f}%)"
                elif result['signal'] == 'SELL':
                    # Only sell on technical signal if we are at least break-even?
                    # Or trust the kill switch. Assuming Kill Switch (-10) means danger.
                    action = 'SELL'
                    reason = f"📉 Technical Breakdown (RSI: {result.get('rsi', 0):.1f})"

                if action == 'SELL':
                    logger.info(f"Selling {symbol}: {reason}")
                    receipt = self.trader.sell(symbol, curr_price)
                    if receipt:
                        pnl_emoji = "🤑" if receipt['pnl'] > 0 else "📉"
                        fee_lbl = "0%" if is_cad else "1.5% x2"
                        msg = (
                            f"{pnl_emoji} *SELL EXEC: {symbol}*\n"
                            f"**Reason:** {reason}\n"
                            f"**Price:** ${receipt['exit_price']:.2f}\n"
                            f"**Net P&L:** ${receipt['pnl']:.2f} ({receipt['pnl_percent']:.2f}%)\n"
                            f"**Fee Structure:** {fee_lbl}\n"
                            f"**Total Equity:** ${self.trader.balance:.2f}"
                        )
                        self.send_telegram_alert(msg)
                else:
                    logger.info(f"✅ Holding {symbol} | Net P&L: {pnl_percent_net:.2f}% | Price: {curr_price:.2f}")
                    
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
