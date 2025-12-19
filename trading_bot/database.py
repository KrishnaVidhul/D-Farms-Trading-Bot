import os
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Text, select, insert, update, delete, func
from sqlalchemy.orm import sessionmaker

# Config
logger = logging.getLogger("Database")
# Default to SQLite for local dev if ENV not set, but Docker will provide Postgres URL
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/trading_bot.db") 

# SQLAlchemy Setup
try:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    metadata = MetaData()
except Exception as e:
    logger.error(f"Failed to create DB engine: {e}")
    engine = None
    metadata = None

# --- Table Definitions ---
fundamentals = Table('fundamentals', metadata,
    Column('symbol', String, primary_key=True),
    Column('pe_ratio', Float),
    Column('last_updated', DateTime)
)

portfolio = Table('portfolio', metadata,
    Column('id', Integer, primary_key=True),
    Column('balance', Float)
)

positions = Table('positions', metadata,
    Column('symbol', String, primary_key=True),
    Column('shares', Float),
    Column('avg_price', Float),
    Column('fee_rate', Float),
    Column('entry_date', String), # Keeping as string to match ISO format usage
    Column('cost_basis', Float),
    Column('entry_price_with_fee', Float)
)

trades = Table('trades', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('symbol', String),
    Column('action', String),
    Column('shares', Float),
    Column('price', Float),
    Column('fee_rate', Float),
    Column('pnl', Float),
    Column('date', DateTime)
)

analysis_log = Table('analysis_log', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('symbol', String),
    Column('timestamp', DateTime),
    Column('volume_ratio', Float),
    Column('sentiment_score', Float),
    Column('pe_ratio', Float),
    Column('technical_signal', String),
    Column('action_taken', String),
    Column('reason', Text),
    Column('price', Float)
)

system_config = Table('system_config', metadata,
    Column('key', String, primary_key=True),
    Column('value', Text),
    Column('updated_at', DateTime, default=datetime.utcnow)
)

response_cache = Table('response_cache', metadata,
    Column('key', String, primary_key=True),
    Column('value', Text),
    Column('expires_at', DateTime)
)

# --- Init ---
def init_db():
    if not engine: return
    try:
        metadata.create_all(engine)
        
        # Init Portfolio with check
        with engine.begin() as conn:
            result = conn.execute(select(portfolio)).fetchone()
            if result is None:
                # Default to $10,000
                conn.execute(insert(portfolio).values(id=1, balance=10000.0))
                
        logger.info("Database initialized successfully (SQLAlchemy).")
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")

# --- Fundamentals ---
def get_fundamental(symbol):
    if not engine: return None
    try:
        with engine.connect() as conn:
            stmt = select(fundamentals.c.pe_ratio, fundamentals.c.last_updated).where(fundamentals.c.symbol == symbol)
            row = conn.execute(stmt).fetchone()
            if row:
                last_updated = row.last_updated
                if datetime.now() - last_updated < timedelta(hours=24):
                    return row.pe_ratio
        return None
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

def set_fundamental(symbol, pe_ratio):
    if not engine: return
    try:
        with engine.begin() as conn:
            # Upsert Logic: Delete then Insert (Simplest cross-dialect for single row)
            conn.execute(delete(fundamentals).where(fundamentals.c.symbol == symbol))
            conn.execute(insert(fundamentals).values(
                symbol=symbol, pe_ratio=pe_ratio, last_updated=datetime.now()
            ))
    except Exception as e:
        logger.error(f"DB Error: {e}")

# --- Portfolio & Positions ---
def get_balance():
    if not engine: return 0.0
    try:
        with engine.connect() as conn:
            row = conn.execute(select(portfolio.c.balance).where(portfolio.c.id == 1)).fetchone()
            return row.balance if row else 0.0
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return 0.0

def update_balance(new_balance):
    if not engine: return
    try:
        with engine.begin() as conn:
            conn.execute(update(portfolio).where(portfolio.c.id == 1).values(balance=new_balance))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def get_positions():
    if not engine: return {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(positions)).mappings().all()
            result = {}
            for row in rows:
                result[row['symbol']] = dict(row)
                # Cleanup: remove symbol key from inner dict if desired, but keeping all is fine
            return result
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return {}

def add_position(symbol, data):
    if not engine: return
    try:
        with engine.begin() as conn:
            # Upsert
            conn.execute(delete(positions).where(positions.c.symbol == symbol))
            conn.execute(insert(positions).values(
                symbol=symbol,
                shares=data['shares'],
                avg_price=data['avg_price'],
                fee_rate=data['fee_rate'],
                entry_date=data['entry_date'],
                cost_basis=data['cost_basis'],
                entry_price_with_fee=data['entry_price_with_fee']
            ))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def remove_position(symbol):
    if not engine: return
    try:
        with engine.begin() as conn:
            conn.execute(delete(positions).where(positions.c.symbol == symbol))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def log_trade(symbol, action, shares, price, fee_rate, pnl=0.0):
    if not engine: return
    try:
        with engine.begin() as conn:
            conn.execute(insert(trades).values(
                symbol=symbol,
                action=action,
                shares=shares,
                price=price,
                fee_rate=fee_rate,
                pnl=pnl,
                date=datetime.now()
            ))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def get_trade_count():
    if not engine: return 0
    try:
        with engine.connect() as conn:
            return conn.execute(select(func.count()).select_from(trades)).scalar()
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return 0

def get_all_trades():
    if not engine: return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(trades).order_by(trades.c.date.desc())).mappings().all()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return []

def log_analysis(symbol, volume_ratio, sentiment_score, pe_ratio, technical_signal, action_taken, reason, price):
    if not engine: return
    try:
        with engine.begin() as conn:
            conn.execute(insert(analysis_log).values(
                symbol=symbol,
                timestamp=datetime.now(),
                volume_ratio=volume_ratio,
                sentiment_score=sentiment_score,
                pe_ratio=pe_ratio,
                technical_signal=technical_signal,
                action_taken=action_taken,
                reason=reason,
                price=price
            ))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def get_recent_analysis(limit=1000):
    if not engine: return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(analysis_log).order_by(analysis_log.c.timestamp.desc()).limit(limit)).mappings().all()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return []

def get_analysis_stats():
    if not engine: return None
    try:
        with engine.connect() as conn:
            start_time = datetime.now() - timedelta(hours=24)
            
            # Total
            total = conn.execute(select(func.count()).select_from(analysis_log).where(analysis_log.c.timestamp > start_time)).scalar()
            
            # Unique
            unique = conn.execute(select(func.count(func.distinct(analysis_log.c.symbol))).where(analysis_log.c.timestamp > start_time)).scalar()
            
            # Actions
            action_rows = conn.execute(
                select(analysis_log.c.action_taken, func.count(analysis_log.c.action_taken))
                .where(analysis_log.c.timestamp > start_time)
                .group_by(analysis_log.c.action_taken)
            ).all()
            actions = {row[0]: row[1] for row in action_rows}
            
            return {
                'total_analyzed': total,
                'unique_analyzed': unique,
                'actions': actions
            }
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

# --- Configuration & Cache ---
def init_kv_tables():
    # Calling create_all in init_db handles this
    pass

def set_config(key, value):
    if not engine: return
    try:
        with engine.begin() as conn:
            conn.execute(delete(system_config).where(system_config.c.key == key))
            conn.execute(insert(system_config).values(key=key, value=json.dumps(value), updated_at=datetime.utcnow()))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def get_config(key, default=None):
    if not engine: return default
    try:
        with engine.connect() as conn:
            row = conn.execute(select(system_config.c.value).where(system_config.c.key == key)).fetchone()
            if row: return json.loads(row.value)
            return default
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return default

def set_cache(key, value, ttl_minutes=60):
    if not engine: return
    try:
        with engine.begin() as conn:
            expires = datetime.now() + timedelta(minutes=ttl_minutes)
            conn.execute(delete(response_cache).where(response_cache.c.key == key))
            conn.execute(insert(response_cache).values(key=key, value=json.dumps(value), expires_at=expires))
    except Exception as e:
        logger.error(f"DB Error: {e}")

def get_cache(key):
    if not engine: return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                select(response_cache.c.value)
                .where(response_cache.c.key == key)
                .where(response_cache.c.expires_at > datetime.now())
            ).fetchone()
            if row: return json.loads(row.value)
            return None
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

# Init Tables
if engine:
    init_db()
