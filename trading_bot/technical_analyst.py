import yfinance as yf
import pandas as pd
import ta
import logging
import asyncio

logger = logging.getLogger("TechnicalAnalyst")

class TechnicalAnalyst:
    """
    A Technical Analysis Agent calculating key indicators (SMA, RSI, BB)
    to generate trading signals for a given ticker (default: SPY).
    Uses 'ta' library.
    """

    def __init__(self, ticker: str = "SPY"):
        self.ticker = ticker

    async def fetch_data(self) -> pd.DataFrame:
        """
        Fetches last 365 days of daily data for the ticker.
        """
        try:
            df = await asyncio.to_thread(yf.download, self.ticker, period="365d", interval="1d", progress=False)
            
            if df.empty:
                logger.error(f"No data fetched for {self.ticker}")
                return pd.DataFrame()
            
            if isinstance(df.columns, pd.MultiIndex):
                # Handle yfinance 0.2+ multi-index structure
                try:
                    df = df.xs(self.ticker, axis=1, level=1, drop_level=True)
                except KeyError:
                    # Case where XS might fail if level is wrong or structure differs
                    pass

            # Ensure we have a Close column, if not try the first column or assume single level
            if 'Close' not in df.columns:
                 # Last resort cleanup
                 if len(df.columns) == 1:
                     df.columns = ['Close'] # Dangerous but works for simple series
            
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {self.ticker}: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates SMA_50, SMA_200, RSI_14, BB_20_2 using 'ta'.
        """
        try:
            if len(df) < 200:
                logger.warning("Not enough data for 200 SMA")
                return df

            # Clean NaNs
            df = df.dropna()

            # SMA
            df['SMA_50'] = ta.trend.SMAIndicator(close=df['Close'], window=50).sma_indicator()
            df['SMA_200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()

            # RSI
            df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()

            # Bollinger Bands
            bb_indicator = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
            df['BB_L'] = bb_indicator.bollinger_lband()
            df['BB_U'] = bb_indicator.bollinger_hband()
            
            return df
        except Exception as e:
            logger.error(f"Indicator calculation failed: {e}")
            return df

    async def analyze(self) -> dict:
        """
        Main method to perform analysis and return signal.
        """
        df = await self.fetch_data()
        if df.empty:
            return {'signal': 'HOLD', 'confidence': 'Low', 'reasoning': 'No Data'}

        df = self.calculate_indicators(df)
        if 'SMA_200' not in df.columns:
             return {'signal': 'HOLD', 'confidence': 'Low', 'reasoning': 'Insufficient Data'}
        
        # Determine latest valid index
        if df['SMA_200'].isna().all():
             return {'signal': 'HOLD', 'confidence': 'Low', 'reasoning': 'Indicators NaN'}

        # Get latest row (ensure not NaN)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0
        reasons = []

        # 1. 📈 Trend Check (Bullish Swing)
        # Price MUST be above SMA 50
        if curr['Close'] > curr['SMA_50']:
            score += 1
            reasons.append("Price > SMA 50")
        else:
            reasons.append("Below SMA 50 (No Trend)")
            return {'signal': 'HOLD', 'confidence': 'Low', 'reasoning': "Below SMA 50", 'latest_price': float(curr['Close']), 'rsi': float(curr['RSI'])}

        # 2. 🚀 Momentum (RSI Rising)
        # RSI Sweet Spot: 40 - 70
        curr_rsi = curr['RSI']
        prev_rsi = prev['RSI']
        
        if 40 <= curr_rsi <= 70:
            if curr_rsi > prev_rsi:
                score += 2 # Strong Signal
                reasons.append(f"RSI Rising ({prev_rsi:.1f} -> {curr_rsi:.1f})")
            else:
                score += 1
                reasons.append(f"RSI Healthy ({curr_rsi:.1f})")
        
        # 3. ⚠️ Overbought Filter
        if curr_rsi > 75:
            score = -10 # KILL SWITCH
            reasons.append(f"RSI Overbought ({curr_rsi:.1f})")

        # 4. Golden Cross (Bonus)
        if prev['SMA_50'] < prev['SMA_200'] and curr['SMA_50'] >= curr['SMA_200']:
            score += 1
            reasons.append("GOLDEN CROSS")

        # Voting
        signal = "HOLD"
        confidence = "Low"
        
        # Need at least Trend + Momentum
        if score >= 3:
            signal = "BUY"
            confidence = "High"
        elif score >= 2:
            signal = "BUY"
            confidence = "Medium"
        elif score < 0:
            # Maybe SELL signal if we owned it, but this is entry logic
            signal = "HOLD" 
            
        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': "; ".join(reasons),
            'latest_price': float(curr['Close']),
            'rsi': float(curr_rsi)
        }

if __name__ == "__main__":
    async def test():
        analyst = TechnicalAnalyst()
        print(await analyst.analyze())
    asyncio.run(test())
