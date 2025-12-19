import os
import json
import logging
from paper_trader import PaperTrader

# Mock Configuration
TEST_FILE = "data/test_portfolio.json"
import paper_trader
paper_trader.DATA_FILE = TEST_FILE
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSim")

def run_simulation():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    print("🚀 Starting Wealthsimple Logic Simulation...")
    trader = PaperTrader()
    
    # TEST 1: US Stock (Fee 1.5%)
    print("\n--- TEST 1: BUY 'NVDA' (US) ---")
    import database as db
    db.update_balance(2000.0) # Update DB so reload_state() gets correct value
    trader.reload_state()
    price_us = 100.0
    
    receipt = trader.buy("NVDA", price_us)
    shares = receipt['shares']
    fee_used = receipt['fee_rate']
    
    assert fee_used == 0.015, f"❌ US Fee Incorrect! Got {fee_used}"
    print(f"✅ US Fee Rate: {fee_used*100}%")
    print(f"Break-Even: ${receipt['break_even']:.2f}")

    # TEST 2: CAD Stock (Fee 0%)
    print("\n--- TEST 2: BUY 'SHOP.TO' (CAD) ---")
    db.update_balance(2000.0)
    trader.reload_state()
    price_cad = 100.0
    
    receipt_cad = trader.buy("SHOP.TO", price_cad)
    fee_used_cad = receipt_cad['fee_rate']
    
    assert fee_used_cad == 0.0, f"❌ CAD Fee Incorrect! Got {fee_used_cad}"
    print(f"✅ CAD Fee Rate: {fee_used_cad*100}%")
    print(f"Break-Even: ${receipt_cad['break_even']:.2f}")
    
    print("\n🎉 WEALTHSIMPLE LOGIC VERIFIED.")
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

if __name__ == "__main__":
    run_simulation()
