import logging
import database as db
from datetime import datetime

logger = logging.getLogger("PaperTrader")

INITIAL_CAPITAL = 360.0 
TRADE_ALLOCATION = 0.20 

class PaperTrader:
    def __init__(self):
        # Initialize DB on startup
        db.init_db()
        self.reload_state()

    def reload_state(self):
        """Refreshes local state from DB."""
        self.balance = db.get_balance()
        self.positions = db.get_positions()
        logger.info(f"Portfolio loaded. Balance: ${self.balance:.2f}")

    def get_fee_rate(self, symbol):
        """
        Wealthsimple Logic:
        - TSX Stocks (.TO): 0.0 (Free)
        - US Stocks (Others): 0.015 (1.5% FX Fee)
        """
        if symbol.endswith('.TO'):
            return 0.0
        return 0.015

    def buy(self, symbol, price):
        self.reload_state() # Ensure fresh balance
        
        if symbol in self.positions:
            return None

        # Allocation Logic
        allocation = self.balance * TRADE_ALLOCATION
        if allocation < 50: 
             return None

        fee_rate = self.get_fee_rate(symbol)
        
        # Cost per share = Price * (1 + Fee)
        # Cost per share = Price * (1 + Fee)
        cost_per_share = price * (1 + fee_rate)
        
        # FRACTIONAL SHARES SUPPORT (Crypto/High-Priced Stocks)
        raw_shares = allocation / cost_per_share
        shares = round(raw_shares, 4) # 4 decimal places
        
        if shares <= 0:
            return None
        
        total_cost = shares * cost_per_share
        
        # Update DB
        new_balance = self.balance - total_cost
        db.update_balance(new_balance)
        
        position_data = {
            'shares': shares,
            'avg_price': price, 
            'fee_rate': fee_rate,
            'entry_price_with_fee': cost_per_share, # True break-even
            'entry_date': datetime.now().isoformat(),
            'cost_basis': total_cost
        }
        db.add_position(symbol, position_data)
        db.log_trade(symbol, 'BUY', shares, price, fee_rate)
        
        self.reload_state()
        
        logger.info(f"BUY: {symbol} | Shares: {shares} | Price: ${price:.2f} | Fee: {fee_rate*100:.1f}%")
        return {
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'fee_rate': fee_rate,
            'break_even': cost_per_share,
            'cost': total_cost
        }

    def sell(self, symbol, price):
        self.reload_state()
        
        if symbol not in self.positions:
            return None
            
        pos = self.positions[symbol]
        shares = pos['shares']
        fee_rate = self.get_fee_rate(symbol)
        
        # Proceeds = (Shares * Price) * (1 - Fee)
        raw_value = shares * price
        proceeds = raw_value * (1 - fee_rate)
        
        initial_cost = pos['cost_basis']
        pnl = proceeds - initial_cost
        pnl_percent = (pnl / initial_cost) * 100
        
        # Update DB
        new_balance = self.balance + proceeds
        db.update_balance(new_balance)
        db.remove_position(symbol)
        db.log_trade(symbol, 'SELL', shares, price, fee_rate, pnl)
        
        # Record for return
        record = {
            'symbol': symbol,
            'action': 'SELL',
            'entry_date': pos['entry_date'],
            'exit_date': datetime.now().isoformat(),
            'entry_price': pos['avg_price'],
            'exit_price': price,
            'fee_rate': fee_rate,
            'pnl': pnl,
            'pnl_percent': pnl_percent
        }
        
        self.reload_state()
        logger.info(f"SELL: {symbol} | P&L: ${pnl:.2f} ({pnl_percent:.2f}%)")
        return record

    def get_summary(self):
        self.reload_state()
        return {
            'cash': self.balance,
            'open_positions': len(self.positions),
            'realized_trades': db.get_trade_count()
        }
