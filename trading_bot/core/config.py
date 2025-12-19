
import os
from dotenv import load_dotenv

load_dotenv()

# Wealthsimple: Free for TSX (.TO), 1.5% Fee for US
INDEX_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
TICKERS = ['SHOP.TO', 'HUT.TO', 'BITF.TO', 'HIVE.TO', 'NVDA', 'COIN']
CRYPTO_TICKERS = ['HUT.TO', 'BITF.TO', 'HIVE.TO', 'COIN', 'BTC-USD', 'ETH-USD']

DEFAULT_SENTIMENT = 0.90
DEFAULT_VOL_MULT = 1.2
STRICT_SENTIMENT = 0.98
STRICT_VOL_MULT = 3.0

BATCH_SIZE = 100 
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
CHECK_INTERVAL_SECONDS = 60 
