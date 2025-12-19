import sys
import os
import json
import logging
import re

# Ensure we can import core from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from core.llm_brain import IntelligentBrain

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ManagerOtto")

class Otto:
    def __init__(self):
        self.brain = IntelligentBrain()
        self.name = "Otto (The CEO)"

    def morning_briefing(self, daily_pnl, news_summary, market_bias):
        """
        Decides budget allocation based on PnL and News.
        Returns: {'stock_agent': float, 'crypto_agent': float}
        """
        logger.info(f"☕ Otto's Morning Briefing: PnL=${daily_pnl}, Bias={market_bias}")
        
        system_prompt = (
            "You are Otto, the CEO of a hedge fund. "
            "Your job is to allocate capital between the StockAgent (Stability) and CryptoAgent (High Risk). "
            "Return the allocation as a strict JSON object with keys 'stock_agent' and 'crypto_agent'. "
            "The sum of values must be <= 1.0. "
            "Example: {\"stock_agent\": 0.7, \"crypto_agent\": 0.3} "
            "Do not output markdown or explanation. Just JSON."
        )

        user_prompt = (
            f"Yesterday we made ${daily_pnl}. "
            f"The market news is: {news_summary}. "
            f"Market Bias is {market_bias}. "
            "Decide the budget allocation for StockAgent and CryptoAgent (0.0 to 1.0)."
        )

        try:
            # 1. Ask Brain (Fast Think via Groq)
            raw_response = self.brain.fast_think(user_prompt, system_prompt)
            logger.info(f"🧠 Otto's Brain Output: {raw_response}")

            # 2. Parse JSON (Handle Markdown wrapping like ```json ... ```)
            json_str = self._clean_json(raw_response)
            allocation = json.loads(json_str)

            # 3. Validate & Safety
            stock_alloc = float(allocation.get('stock_agent', 0.5))
            crypto_alloc = float(allocation.get('crypto_agent', 0.0))

            # Safety Cap: Normalize if > 1.0
            total = stock_alloc + crypto_alloc
            if total > 1.0:
                logger.warning(f"⚠️ Allocation > 100% ({total}). Normalizing...")
                stock_alloc = stock_alloc / total
                crypto_alloc = crypto_alloc / total
            
            # Final Result
            result = {
                "stock_agent": round(stock_alloc, 2),
                "crypto_agent": round(crypto_alloc, 2)
            }
            logger.info(f"✅ Final Allocation: {result}")
            return result

        except Exception as e:
            logger.error(f"🔥 Otto crashed during briefing: {e}. Using defensive fallback.")
            return {"stock_agent": 0.8, "crypto_agent": 0.0} # Safe fallback

    def _clean_json(self, text):
        """Extract JSON structure from potential markdown"""
        # Remove ```json and ```
        text = re.sub(r'```json', '', text)
        text = re.sub(r'```', '', text)
        
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

if __name__ == "__main__":
    # Test Run
    otto = Otto()
    
    # Scene 1: Good news, profit
    print("\n--- Scene 1: Bull Market ---")
    alloc1 = otto.morning_briefing(
        daily_pnl=500.0, 
        news_summary="Fed cuts interest rates. SPY hits all time high.", 
        market_bias="BULLISH"
    )
    print(f"Result: {alloc1}")

    # Scene 2: Bad news, loss
    print("\n--- Scene 2: Bear Market ---")
    alloc2 = otto.morning_briefing(
        daily_pnl=-200.0, 
        news_summary="Bitcoin crashes 10% on regulation fears. Inflation rises.", 
        market_bias="BEARISH"
    )
    print(f"Result: {alloc2}")
