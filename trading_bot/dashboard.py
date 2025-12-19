import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
import sqlite3
from datetime import datetime, timedelta
import database as db
from streamlit_autorefresh import st_autorefresh
import requests

# Page Config
st.set_page_config(
    page_title="Trading Bot Dashboard 🦅",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-Refresh Logic
st_autorefresh(interval=30000, key="data_refresh")

# --- Boardroom Strategy Section ---
st.markdown("### 🧠 Boardroom Strategy")
col1, col2, col3, col4 = st.columns(4)

# Fetch Strategy Data
budget = db.get_config("budget_allocation", default={'stock_agent': 0.5, 'crypto_agent': 0.5})
bias = db.get_config("market_bias", default="NEUTRAL")
last_brief = db.get_cache("market_brief_v2") # Just to check if fresh

with col1:
    bias_emoji = "✅" if bias == 'BUY' else ("🛑" if bias == 'SELL' else "⚖️")
    st.metric("Market Bias", f"{bias} {bias_emoji}")

with col2:
    st.metric("Stock Budget", f"{budget.get('stock_agent', 0.5)*100:.0f}%", "Stability")

with col3:
    st.metric("Crypto Budget", f"{budget.get('crypto_agent', 0.5)*100:.0f}%", "High Risk")

with col4:
    # Estimate sync time (mock for now, or fetch config timestamp if available)
    st.metric("Orchestrator", "Active", "Syncing...")

st.markdown("---")

def load_data():
    balance = db.get_balance()
    positions = db.get_positions()
    trades = db.get_all_trades()
    return balance, positions, trades

@st.cache_data(ttl=86400) # Cache for 24h
def get_ticker_map():
    """Fetch S&P 500 components for Name mapping"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            return {}
            
        tables = pd.read_html(r.text)
        df = tables[0]
        # Create dict: Symbol -> Security Name
        ticker_map = dict(zip(df['Symbol'], df['Security']))
        
        # Add custom watchlist mapping manually
        custom_map = {
            'SHOP.TO': 'Shopify Inc (TSX)',
            'HUT.TO': 'Hut 8 Corp (TSX)',
            'BITF.TO': 'Bitfarms Ltd (TSX)',
            'HIVE.TO': 'HIVE Digital (TSX)',
            'BTC-USD': 'Bitcoin'
        }
        ticker_map.update(custom_map)
        return ticker_map
    except Exception as e:
        # st.warning(f"Name Fetch Failed: {e}") # Debug only
        return {}

def load_oci_costs():
    """Load OCI cost data from monitoring database"""
    try:
        # Check mounted volume first, fallback to local (dev)
        cost_db_mounted = "/app/monitor_data/oci/costs.db"
        cost_db_local = os.path.expanduser("~/oci_monitor/costs.db")
        
        cost_db = cost_db_mounted if os.path.exists(cost_db_mounted) else cost_db_local
        
        if not os.path.exists(cost_db):
            return None
        
        conn = sqlite3.connect(cost_db)
        query = "SELECT timestamp, amount FROM hourly_costs ORDER BY timestamp DESC LIMIT 168"  # Last 7 days
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return None
    except Exception as e:
        st.error(f"Error loading cost data: {e}")
        return None

def get_sniper_history():
    """Read sniper log history"""
    try:
        log_mounted = "/app/monitor_data/sniper/sniper.log"
        log_local = os.path.expanduser("~/arm_sniper/sniper.log")
        
        log_file = log_mounted if os.path.exists(log_mounted) else log_local
        
        if not os.path.exists(log_file):
            return []
            
        history = []
        with open(log_file, 'r') as f:
            # Read last 50 lines
            lines = f.readlines()[-50:]
            for line in lines:
                parts = line.strip().split(' - ')
                if len(parts) >= 2:
                    ts = parts[0]
                    msg = parts[-1]
                    status = "✅" if "CAPACITY" in msg else "❌" if "No capacity" in msg else "ℹ️"
                    history.append({"Time": ts, "Status": status, "Message": msg})
        
        return list(reversed(history)) # Newest first
    except:
        return []

def get_sniper_status():
    """Check ARM sniper status"""
    try:
        log_mounted = "/app/monitor_data/sniper/sniper.log"
        log_local = os.path.expanduser("~/arm_sniper/sniper.log")
        prov_mounted = "/app/monitor_data/sniper/.provisioned"
        prov_local = os.path.expanduser("~/arm_sniper/.provisioned")
        
        sniper_log = log_mounted if os.path.exists(log_mounted) else log_local
        provisioned_flag = prov_mounted if os.path.exists(prov_mounted) else prov_local
        
        if os.path.exists(provisioned_flag):
            with open(provisioned_flag, 'r') as f:
                provision_time = f.read().strip()
            return {
                'status': '✅ Provisioned',
                'message': f'ARM instance created at {provision_time}',
                'active': False
            }
        
        if os.path.exists(sniper_log):
            # Read last few lines
            with open(sniper_log, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1]
                    if 'No capacity available' in last_line:
                        return {
                            'status': '🔍 Monitoring',
                            'message': 'Checking every 5 minutes for Ampere A1 availability',
                            'active': True
                        }
                    elif 'CAPACITY DETECTED' in last_line:
                        return {
                            'status': '⚡ Provisioning',
                            'message': 'Capacity detected! Creating instance...',
                            'active': True
                        }
        
        return {
            'status': '⏳ Waiting',
            'message': 'Sniper initialized, waiting for first check',
            'active': True
        }
    except Exception:
        return {
            'status': '❓ Unknown',
            'message': 'Unable to read sniper status',
            'active': False
        }


# --- MAIN UI ---
st.title("🦅 Trading Bot Live Command")

# Load Data
balance, positions, trades = load_data()

# --- METRICS CALCULATION ---
invested_capital = 0.0
active_positions_count = 0
portfolio_dist = []

if positions:
    active_positions_count = len(positions)
    for sym, data in positions.items():
        # Estimate value based on Cost Basis (since we lack live price feed here without slowing down)
        # Ideally, we'd fetch live price, but let's use cost basis as proxy for "Invested Amount"
        val = data['shares'] * data['avg_price']
        invested_capital += val
        portfolio_dist.append({'Symbol': sym, 'Value': val})

total_equity = balance + invested_capital
total_pnl = 0.0
win_rate = 0.0
trade_count = len(trades)

if trades:
    df_trades = pd.DataFrame(trades)
    total_pnl = df_trades['pnl'].sum()
    wins = df_trades[df_trades['pnl'] > 0]
    if len(df_trades) > 0:
        win_rate = (len(wins) / len(df_trades)) * 100

# Top Row Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Equity (Est)", f"${total_equity:,.2f}")
with col2:
    st.metric("Cash (Buying Power)", f"${balance:,.2f}")
with col3:
    st.metric("Invested Capital", f"${invested_capital:,.2f}", f"{active_positions_count} Active")
with col4:
    color = "normal"
    st.metric("Realized P&L", f"${total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")

st.divider()

# Create tabs - Reordered for better UX
tab1, tab2, tab3, tab4 = st.tabs(["🔴 Live Activity", "🤖 Decision Log", "📜 Trade History", "🏗️ Infrastructure"])

with tab1: 
    # Combine Boardroom + Positions
    col_board, col_pos = st.columns([1, 2])
    
    with col_board:
        st.subheader("Briefing")
        brief = db.get_cache("market_brief_v2")
        if brief:
            st.markdown(brief)
        else:
            st.caption("Waiting for morning update...")
            
        # Distribution Chart
        if portfolio_dist:
             df_dist = pd.DataFrame(portfolio_dist)
             fig = px.pie(df_dist, values='Value', names='Symbol', hole=0.4, title="Portfolio Allocation")
             fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=250, showlegend=False)
             st.plotly_chart(fig, use_container_width=True)
    
    with col_pos:
        st.subheader("Active Holdings")
        if positions:
            ticker_map = get_ticker_map()
            pos_list = []
            for sym, data in positions.items():
                data['symbol'] = sym
                data['name'] = ticker_map.get(sym, sym)
                entry_date = datetime.fromisoformat(data['entry_date'])
                days = (datetime.now() - entry_date).days + (datetime.now() - entry_date).seconds / 86400
                data['days_held'] = days
                pos_list.append(data)
            
            df_pos = pd.DataFrame(pos_list)
            df_pos = df_pos[['symbol', 'name', 'shares', 'avg_price', 'days_held', 'cost_basis']]
            
            st.dataframe(
                df_pos, 
                use_container_width=True,
                column_config={
                    "symbol": "Ticker",
                    "name": "Company",
                    "shares": "Qty",
                    "avg_price": st.column_config.NumberColumn("Avg Price", format="$%.2f"),
                    "cost_basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
                    "days_held": st.column_config.ProgressColumn(
                        "Days Held", 
                        min_value=0, 
                        max_value=5, 
                        format="%.1f days"
                    )
                },
                hide_index=True
            )
        else:
             st.info("No active positions. Cash is king! 👑")

with tab2:
    st.subheader("🤖 Bot Brain Analysis")
    
    # Get analysis data
    analysis_data = db.get_recent_analysis(limit=5000)
    
    if analysis_data:
        df_analysis = pd.DataFrame(analysis_data)
        df_analysis['timestamp'] = pd.to_datetime(df_analysis['timestamp'])
        
        # KEY CHANGE: Default Filters
        # Only show interesting events by default
        default_actions = ['BOUGHT', 'SOLD', 'BUY_SIGNAL', 'SELL_SIGNAL']
        available_actions = df_analysis['action_taken'].unique().tolist()
        
        # Ensure defaults exist in available
        defaults = [x for x in default_actions if x in available_actions]
        # If regular 'BUY' / 'SELL' exist in DB from old logs, include them
        defaults.extend([x for x in ['BUY', 'SELL'] if x in available_actions])
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            action_filter = st.multiselect(
                "Filter Log Events",
                options=available_actions,
                default=defaults if defaults else available_actions
            )
        with col_filter2:
             st.caption("ℹ️ 'INSUFFICIENT_FUNDS' and 'REJECTED' are hidden by default to reduce noise.")

        filtered_df = df_analysis[df_analysis['action_taken'].isin(action_filter)]
        filtered_df = filtered_df.sort_values('timestamp', ascending=False)
        
        # Add Names
        ticker_map = get_ticker_map()
        filtered_df['name'] = filtered_df['symbol'].map(ticker_map).fillna(filtered_df['symbol'])
        
        # Formatting for Table
        display_df = filtered_df[['timestamp', 'symbol', 'name', 'action_taken', 'reason', 'sentiment_score', 'pe_ratio', 'price']].head(500).copy()
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
        display_df['sentiment_score'] = pd.to_numeric(display_df['sentiment_score'], errors='coerce').round(2)
        display_df['pe_ratio'] = pd.to_numeric(display_df['pe_ratio'], errors='coerce').round(1)
        
        # Rename
        display_df.columns = ['Time', 'Symbol', 'Name', 'Action', 'Reason', 'Sentiment', 'P/E', 'Price']
        
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Reason": st.column_config.TextColumn("Reason", width="large"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Sentiment": st.column_config.NumberColumn("Sent", format="%.2f"),
            }
        )
    else:
        st.info("No analysis logs found.")

with tab3:
    st.subheader("📜 Trade History")
    if trades:
        df_trades = pd.DataFrame(trades)
        df_trades['date'] = pd.to_datetime(df_trades['date'])
        df_trades = df_trades.sort_values(by='date', ascending=False)
        
        # PnL Chart
        fig = px.bar(df_trades, x='date', y='pnl', title="Realized PnL per Trade", color='pnl', color_continuous_scale=['red', 'green'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_trades, use_container_width=True, hide_index=True)
    else:
        st.write("No trades executed yet.")

with tab4:
    st.subheader("🏗️ Infrastructure & Costs")
    
    # OCI Cost Tracking
    cost_data = load_oci_costs()
    if cost_data is not None and not cost_data.empty:
        # Data is cumulative (MTD), so we don't sum it.
        # Latest value is the current month's bill.
        # Note: SQL query orders DESC, so iloc[0] is newest
        current_cost = cost_data['amount'].iloc[0]
        
        # Calculate 24h Burn (Change in last 24h)
        last_24h = cost_data[cost_data['timestamp'] > (datetime.now() - timedelta(hours=24))]
        
        daily_burn = 0.0
        if not last_24h.empty:
            cost_24h_ago = last_24h['amount'].iloc[-1]  # Oldest in 24h window
            daily_burn = current_cost - cost_24h_ago
        
        # Display Metrics
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.metric("Total Project Cost", f"${current_cost:.2f}")
        with col_c2:
            st.metric("Daily Burn (24h)", f"${daily_burn:.2f}", delta="Est. Daily Rate")
        
        fig = px.line(cost_data, x='timestamp', y='amount', title="Cumulative Cost (MTD)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cost data unavailable.")
    
    st.divider()
    
    # Sniper
    sniper_status = get_sniper_status()
    st.markdown(f"**ARM Sniper Status:** {sniper_status['status']}")
    st.caption(sniper_status['message'])
    
    history = get_sniper_history()
    if history:
        with st.expander("View Sniper Logs"):
            st.dataframe(pd.DataFrame(history), use_container_width=True)


if st.button("Refresh Data 🔄"):
    st.rerun()

st.caption(f"Last Updated: {time.strftime('%H:%M:%S')} | Auto-refresh: 30s")
