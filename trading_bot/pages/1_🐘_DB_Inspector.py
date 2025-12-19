import streamlit as st
import pandas as pd
import database as db
from sqlalchemy import inspect, text

st.set_page_config(page_title="DB Inspector", page_icon="🐘", layout="wide")

st.title("🐘 PostgreSQL Inspector")

# Password Protection (Optional simple strictness)
# For now, open since it is internal tool protected by OCI firewall/ssh usually.
# But adding a simple confirm.

if not db.engine:
    st.error("❌ Database Engine not connected!")
    st.stop()

# 1. Inspector Tab
tab1, tab2 = st.tabs(["🔎 Table Viewer", "👨‍💻 SQL Runner"])

with tab1:
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        selected_table = st.selectbox("Select Table", tables, index=0 if tables else None)
        
        if selected_table:
            # Get Row Count
            with db.engine.connect() as conn:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {selected_table}")).scalar()
            
            st.metric(f"Rows in '{selected_table}'", count)
            
            # Fetch Data
            limit = st.slider("Limit rows", 10, 1000, 100)
            order_col = st.text_input("Order By Column (Optional)", "")
            
            query = f"SELECT * FROM {selected_table}"
            if order_col:
                query += f" ORDER BY {order_col} DESC"
            query += f" LIMIT {limit}"
            
            df = pd.read_sql(query, db.engine)
            st.dataframe(df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error inspecting DB: {e}")

with tab2:
    st.markdown("### Run Raw SQL")
    st.warning("⚠️ Be careful! This executes directly against the production database.")
    
    query = st.text_area("SQL Query", "SELECT * FROM trades LIMIT 10;", height=150)
    
    if st.button("Run Query 🚀"):
        try:
            with db.engine.connect() as conn:
                # Use pandas for Clean Table result
                # Check if it modifies data
                lower_q = query.strip().lower()
                if any(x in lower_q for x in ['update', 'delete', 'drop', 'insert', 'alter']):
                    # Execute and Commit
                    result = conn.execute(text(query))
                    conn.commit()
                    st.success(f"Executed. Rows affected: {result.rowcount}")
                else:
                    # Read only
                    df = pd.read_sql(text(query), conn)
                    st.dataframe(df, use_container_width=True)
                    st.success(f"Returned {len(df)} rows.")
                    
        except Exception as e:
            st.error(f"SQL Error: {e}")

# Footer Stats
st.divider()
try:
    with db.engine.connect() as conn:
        ver = conn.execute(text("SELECT version();")).scalar()
        st.caption(f"Connected to: {ver}")
except:
    pass
