import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import numpy as np
import json
import pickle
from datetime import datetime

"""
TO RUN:
streamlit run bot/dashboard/app.py
"""

# Set page config
# st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")

# Paths
DATA_DIR = "bot/logs"
EQUITY_FILE = os.path.join(DATA_DIR, "equity_history.csv")
TRADE_FILE = os.path.join(DATA_DIR, "trade_history.csv")
POSITIONS_FILE = os.path.join(DATA_DIR, "current_positions.csv")
CONFIG_FILE = "bot/config/config.json"
KLINES_CACHE_DIR = "bot/data/klines_cache"

def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

def load_config_coins(config_path):
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        coins = set()
        for pair in config.get("trading_pairs", []):
            coins.add(pair["coin_a"])
            coins.add(pair["coin_b"])
        return sorted(list(coins))
    return []

def load_kline_data(coin):
    path = os.path.join(KLINES_CACHE_DIR, f"{coin}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            df = pickle.load(f)
            return df
    return pd.DataFrame()

def calculate_sharpe(returns):
    if len(returns) < 2:
        return 0
    return np.sqrt(24 * 365) * returns.mean() / returns.std() if returns.std() != 0 else 0

st.title("🚀 Strategy Performance Dashboard")

# Sidebar for controls
st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 5, 60, 10)

# Main Dashboard
col1, col2, col3, col4 = st.columns(4)

equity_df = load_data(EQUITY_FILE)
trade_df = load_data(TRADE_FILE)
positions_df = load_data(POSITIONS_FILE)

if not equity_df.empty:
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
    current_equity = equity_df['total_value'].iloc[-1]
    initial_equity = equity_df['total_value'].iloc[0]
    total_return = (current_equity - initial_equity) / initial_equity * 100
    
    equity_df['returns'] = equity_df['total_value'].pct_change()
    sharpe = calculate_sharpe(equity_df['returns'].dropna())

    col1.metric("Total Equity", f"${current_equity:,.2f}")
    col2.metric("Total Return", f"{total_return:.2f}%")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Total Trades", len(trade_df))

    st.subheader("📈 Equity Curve")
    fig_equity = px.line(equity_df, x='timestamp', y='total_value', title="Portfolio Value Over Time")
    fig_equity.update_layout(xaxis_title="Time", yaxis_title="Equity (USD)")
    st.plotly_chart(fig_equity, use_container_width=True)
else:
    st.warning("No equity data found yet. Run the bot to generate data.")

tab1, tab2 = st.tabs(["Active Positions", "Trade History"])

with tab1:
    st.subheader("💼 Real-time Positions")
    if not positions_df.empty:
        st.dataframe(positions_df, use_container_width=True)
    else:
        st.info("No active positions.")

with tab2:
    st.subheader("📜 Recent Trades")
    if not trade_df.empty:
        trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
        st.dataframe(trade_df.sort_values(by='timestamp', ascending=False), use_container_width=True)
    else:
        st.info("No trade history available.")

# Price Charts
st.subheader("📊 Coin Price Analysis")
all_configured_coins = load_config_coins(CONFIG_FILE)

if all_configured_coins:
    selected_coin = st.selectbox("Select a coin to view charts", all_configured_coins)
    cdf = load_kline_data(selected_coin)
    
    if not cdf.empty:
        # Show last 100-200 candles for better visibility
        plot_df = cdf.tail(200).copy()
        plot_df["open_time"] = pd.to_datetime(plot_df["open_time"])
        
        fig_price = go.Figure(data=[go.Candlestick(x=plot_df['open_time'],
                        open=plot_df['open'],
                        high=plot_df['high'],
                        low=plot_df['low'],
                        close=plot_df['close'],
                        name="Price")])
        
        # Add Entry Price Line if held
        if not positions_df.empty:
            coin_pos = positions_df[positions_df['coin'] == selected_coin]
            if not coin_pos.empty:
                entry_price = float(coin_pos.iloc[0]['entry_price'])
                fig_price.add_hline(y=entry_price, line_dash="dash", line_color="green", 
                                   annotation_text=f"Entry: {entry_price:.4f}", 
                                   annotation_position="top left")
                st.success(f"Currently holding {selected_coin} (Entry: {entry_price:.4f})")

        fig_price.update_layout(title=f"{selected_coin}/USD Price Action (from klines_cache)", 
                               xaxis_title="Time", yaxis_title="Price (USD)",
                               height=600)
        st.plotly_chart(fig_price, use_container_width=True)
    else:
        st.warning(f"No cache found for {selected_coin} in {KLINES_CACHE_DIR}.")
else:
    st.info("No coins found in config.json.")
