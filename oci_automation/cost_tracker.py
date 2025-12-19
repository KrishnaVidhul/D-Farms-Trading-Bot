#!/usr/bin/env python3
import os
import sqlite3
import logging
from datetime import datetime, timedelta
import requests

# Configuration
DB_FILE = os.path.expanduser("~/oci_monitor/costs.db")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/oci_monitor/cost_tracker.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CostTracker")

def init_db():
    """Initialize SQLite database for cost tracking"""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hourly_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            amount REAL,
            currency TEXT DEFAULT 'USD'
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def get_oci_costs():
    """
    Fetch current OCI costs using OCI SDK
    Returns: cost amount in USD
    """
    try:
        # Check if OCI is configured
        oci_config = os.path.expanduser("~/.oci/config")
        if not os.path.exists(oci_config):
            logger.warning("OCI credentials not configured. Skipping cost fetch.")
            return None
        
        import oci
        
        # Load OCI config
        config = oci.config.from_file()
        
        # Initialize Usage API client
        usage_client = oci.usage_api.UsageapiClient(config)
        
        # Get costs for the last hour
        end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=1)
        
        request_summarized_usages_details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=config['tenancy'],
            time_usage_started=start_time.isoformat() + 'Z',
            time_usage_ended=end_time.isoformat() + 'Z',
            granularity='HOURLY',
            query_type='COST'
        )
        
        response = usage_client.request_summarized_usages(
            request_summarized_usages_details=request_summarized_usages_details
        )
        
        # Sum up costs
        total_cost = sum(item.computed_amount for item in response.data.items)
        logger.info(f"Fetched OCI cost: ${total_cost:.4f}")
        return total_cost
        
    except ImportError:
        logger.error("OCI SDK not installed. Run: pip install oci")
        return None
    except Exception as e:
        logger.error(f"Error fetching OCI costs: {e}")
        return None

def store_cost(amount):
    """Store cost data in database"""
    if amount is None:
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO hourly_costs (timestamp, amount) VALUES (?, ?)',
        (datetime.now().isoformat(), amount)
    )
    conn.commit()
    conn.close()
    logger.info(f"Stored cost: ${amount:.4f}")

def get_daily_summary():
    """Get cost summary for the last 24 hours"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    yesterday = datetime.now() - timedelta(days=1)
    cursor.execute(
        'SELECT SUM(amount), AVG(amount), MAX(amount), COUNT(*) FROM hourly_costs WHERE timestamp > ?',
        (yesterday.isoformat(),)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] is not None:
        return {
            'total': result[0],
            'average': result[1],
            'peak': result[2],
            'samples': result[3]
        }
    return None

def send_telegram(message):
    """Send message via Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")

def main():
    """Main execution"""
    init_db()
    
    # Fetch and store current cost
    cost = get_oci_costs()
    store_cost(cost)
    
    # Check if it's time for daily report (8 AM)
    now = datetime.now()
    if now.hour == 8 and now.minute < 10:  # Within 10 min window
        summary = get_daily_summary()
        if summary:
            message = f"""
📊 *OCI Daily Cost Report*

💰 *Total (24h):* ${summary['total']:.2f}
📈 *Average/Hour:* ${summary['average']:.4f}
⚡ *Peak Hour:* ${summary['peak']:.4f}
🔢 *Samples:* {summary['samples']}

_Report generated at {now.strftime('%Y-%m-%d %H:%M')} UTC_
"""
            send_telegram(message)

if __name__ == "__main__":
    main()
