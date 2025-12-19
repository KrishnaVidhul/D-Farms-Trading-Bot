
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MOCK ALL DEPENDENCIES
sys.modules['database'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.dialects.postgresql'] = MagicMock()
sys.modules['ta'] = MagicMock()
sys.modules['ta.momentum'] = MagicMock()
sys.modules['ta.trend'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['yfinance'] = MagicMock()
sys.modules['transformers'] = MagicMock()

from core.market_scanner import MarketScanner

class TestMarketScannerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_executor = MagicMock()
        self.mock_executor.log_rejection = AsyncMock()
        self.mock_executor.execute_trade_logic = AsyncMock()
        self.scanner = MarketScanner(self.mock_executor)

    @patch("core.market_scanner.TechnicalAnalyst")
    @patch.object(MarketScanner, "get_symbol_news")
    @patch.object(MarketScanner, "get_fundamentals")
    def test_crypto_bypass_pe(self, MockFund, MockNews, MockTA):
        # Setup Mocks
        MockNews.return_value = ["Bitcoin is up", "Crypto boom"]
        MockFund.return_value = None # Crypto has no P/E
        
        # Inject Sentiment Mock directly
        self.scanner.sentiment_analyzer = MagicMock()
        self.scanner.sentiment_analyzer.analyze.return_value = 0.95
        
        mock_ta_instance = MockTA.return_value
        mock_ta_instance.analyze = AsyncMock(return_value={
            'signal': 'NEUTRAL', 
            'latest_price': 50000
        })
        
        # Test BTC-USD
        asyncio.run(self.scanner.process_candidate(
            "BTC-USD", curr_vol=100, avg_vol=50, sent_thresh=0.8, market_bias="NEUTRAL"
        ))
        
        # Should NOT log rejection for "Extreme Valuation"
        self.mock_executor.execute_trade_logic.assert_called_once()
        self.mock_executor.log_rejection.assert_not_called()

    @patch("core.market_scanner.TechnicalAnalyst")
    @patch.object(MarketScanner, "get_symbol_news")
    @patch.object(MarketScanner, "get_fundamentals")
    def test_high_pe_rejection(self, MockFund, MockNews, MockTA):
        # High P/E Stock, Weak Technicals
        MockNews.return_value = ["Stock is okay"]
        MockFund.return_value = 200.0 # High P/E
        
        self.scanner.sentiment_analyzer = MagicMock()
        self.scanner.sentiment_analyzer.analyze.return_value = 0.95
        
        mock_ta_instance = MockTA.return_value
        mock_ta_instance.analyze = AsyncMock(return_value={
            'signal': 'NEUTRAL', # Not Strong Buy
            'latest_price': 100
        })
        
        asyncio.run(self.scanner.process_candidate(
            "OVERVALUED", curr_vol=100, avg_vol=50, sent_thresh=0.8, market_bias="NEUTRAL"
        ))
        
        # Should REJECT due to P/E > 150 and No Momentum
        self.mock_executor.log_rejection.assert_called_with(
            "OVERVALUED", None, 'Extreme Valuation (P/E 200.0 > 150) & No Momentum', unittest.mock.ANY
        )
        self.mock_executor.execute_trade_logic.assert_not_called()

    @patch("core.market_scanner.TechnicalAnalyst")
    @patch.object(MarketScanner, "get_symbol_news")
    @patch.object(MarketScanner, "get_fundamentals")
    def test_high_pe_momentum_exception(self, MockFund, MockNews, MockTA):
        # High P/E Stock, BUT Strong Technicals
        MockNews.return_value = ["Stock is flying!"]
        MockFund.return_value = 200.0
        
        self.scanner.sentiment_analyzer = MagicMock()
        self.scanner.sentiment_analyzer.analyze.return_value = 0.95
        
        mock_ta_instance = MockTA.return_value
        mock_ta_instance.analyze = AsyncMock(return_value={
            'signal': 'STRONG_BUY', # MOMENTUM!
            'latest_price': 100
        })
        
        asyncio.run(self.scanner.process_candidate(
            "MOMENTUM_STOCK", curr_vol=100, avg_vol=50, sent_thresh=0.8, market_bias="NEUTRAL"
        ))
        
        # Should PASS because of STRONG_BUY exception
        self.mock_executor.execute_trade_logic.assert_called_once()
        self.mock_executor.log_rejection.assert_not_called()

if __name__ == '__main__':
    unittest.main()
