import streamlit as st
import pandas as pd
import plotly.express as px
from pagr.portfolio import Portfolio
from pagr.market_data import get_current_prices, get_sector_info
from pathlib import Path

st.set_page_config(page_title="PAGR - Portfolio Analysis", layout="wide")

st.title("Portfolio Analysis with GraphRag (PAGR)")

# Sidebar for file selection
st.sidebar.header("Portfolio Selection")
uploaded_file = st.sidebar.file_uploader("Upload a .pagr file", type="pagr")

# Load default if no file uploaded
portfolio = None
if uploaded_file is not None:
    # Save uploaded file temporarily to read it
    # Or modify Portfolio.from_file to accept a file-like object
    # For now, let's assume we can read the json directly
    import json
    try:
        data = json.load(uploaded_file)
        # Create a temporary file to use the existing from_file method or refactor
        # Let's refactor Portfolio to take a dict or file path. 
        # For now, I'll just manually construct it here to avoid changing the class too much in this step
        # Actually, let's just write it to a temp file
        with open("temp_portfolio.pagr", "w") as f:
            json.dump(data, f)
        portfolio = Portfolio.from_file("temp_portfolio.pagr")
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
else:
    # Try to load default
    default_path = Path("default_portfolio.pagr")
    if default_path.exists():
        portfolio = Portfolio.from_file(default_path)
    else:
        st.info("Please upload a .pagr file.")

if portfolio:
    st.header(f"Portfolio: {portfolio.name}")
    
    with st.spinner("Fetching market data..."):
        tickers = portfolio.get_tickers()
        prices = get_current_prices(tickers)
        sectors = get_sector_info(tickers)
        
        # Update portfolio positions
        portfolio_data = []
        total_value = 0.0
        
        for pos in portfolio.positions:
            price = prices.get(pos.ticker, 0.0)
            # If price is a Series (sometimes happens with yfinance), get the float value
            if isinstance(price, pd.Series):
                price = price.iloc[0]
            
            # Handle NaN prices
            if pd.isna(price):
                price = 0.0
                
            pos.current_price = float(price)
            pos.sector = sectors.get(pos.ticker, "Unknown")
            pos.market_value = pos.quantity * pos.current_price
            total_value += pos.market_value
            
            portfolio_data.append({
                "Ticker": pos.ticker,
                "Quantity": pos.quantity,
                "Market Price": f"{portfolio.currency} {pos.current_price:,.2f}",
                "Market Value": pos.market_value, # Keep as number for sorting/charting
                "Sector": pos.sector
            })
            
        df = pd.DataFrame(portfolio_data)
        
        # Display Metrics
        st.metric("Total Portfolio Value", f"{portfolio.currency} {total_value:,.2f}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Positions")
            # Format Market Value for display
            display_df = df.copy()
            display_df["Market Value"] = display_df["Market Value"].apply(lambda x: f"{portfolio.currency} {x:,.2f}")
            st.dataframe(display_df, use_container_width=True)
            
        with col2:
            st.subheader("Sector Allocation")
            if not df.empty:
                # Group by sector
                sector_df = df.groupby("Sector")["Market Value"].sum().reset_index()
                # Sort by Market Value descending
                sector_df = sector_df.sort_values("Market Value", ascending=False)
                fig = px.bar(sector_df, x="Sector", y="Market Value", title="Portfolio Value by Sector", color="Sector")
                # Update layout to respect the sort order
                fig.update_layout(xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig, use_container_width=True)
