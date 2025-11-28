import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_agraph import agraph, Node, Edge, Config
from pagr.portfolio import Portfolio
from pagr.market_data import get_current_prices
from pagr import db
from pagr import db
from pathlib import Path
from pagr.agent import get_agent, StatusCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import threading

st.set_page_config(page_title="PAGR - Portfolio Analysis", layout="wide")

st.title("Portfolio Analysis with GraphRag (PAGR)")

# Sidebar for file selection
st.sidebar.header("Portfolio Selection")
uploaded_file = st.sidebar.file_uploader("Upload a .pagr file", type="pagr")

# View Selection
view_selection = st.sidebar.radio("Select View", ["Tabular by Sector", "Graph"])

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
    # Sync to Database
    try:
        portfolio.to_db()
    except Exception as e:
        st.error(f"Failed to sync with database: {e}")
    # Trade In/Out Section
    with st.expander("Trade In/Out"):
        col_trade_1, col_trade_2, col_trade_3 = st.columns([2, 2, 1])
        with col_trade_1:
            trade_ticker = st.text_input("Ticker Symbol").upper()
        with col_trade_2:
            trade_quantity = st.number_input("Quantity (Negative to Sell)", value=0.0, step=1.0)
        with col_trade_3:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("Execute Trade"):
                if not trade_ticker:
                    st.error("Please enter a ticker.")
                elif trade_quantity == 0:
                    st.error("Please enter a non-zero quantity.")
                else:
                    from pagr.market_data import validate_ticker
                    with st.spinner(f"Validating {trade_ticker}..."):
                        if validate_ticker(trade_ticker):
                            portfolio.add_position(trade_ticker, trade_quantity)
                            # Save changes
                            # If loaded from uploaded file, we can't easily save back to user's disk
                            # But if loaded from default or temp, we can save there.
                            # For now, let's assume we save to the path we loaded from if possible.
                            # Since we are using a temp file for uploaded, this persists for the session but not user disk.
                            # If using default, it saves to default.
                            save_path = "temp_portfolio.pagr" if uploaded_file else "default_portfolio.pagr"
                            portfolio.save(save_path)
                            st.success(f"Trade executed: {trade_quantity} {trade_ticker}")
                            st.rerun()
                        else:
                            st.error(f"Invalid ticker: {trade_ticker}")

    st.header(f"Portfolio: {portfolio.name}")
    
    if view_selection == "Tabular by Sector":
        with st.spinner("Fetching market data..."):
            # Fetch view from DB
            try:
                db_positions = db.get_portfolio_view(portfolio.name)
            except Exception as e:
                st.error(f"Error querying database: {e}")
                db_positions = []

            tickers = [p['ticker'] for p in db_positions]
            prices = get_current_prices(tickers)
            
            # Update portfolio positions
            portfolio_data = []
            total_value = 0.0
            
            for pos in db_positions:
                ticker = pos['ticker']
                quantity = pos['quantity']
                sector = pos['sector']
                
                price = prices.get(ticker, 0.0)
                # If price is a Series (sometimes happens with yfinance), get the float value
                if isinstance(price, pd.Series):
                    price = price.iloc[0]
                
                # Handle NaN prices
                if pd.isna(price):
                    price = 0.0
                    
                current_price = float(price)
                market_value = quantity * current_price
                total_value += market_value
                
                portfolio_data.append({
                    "Ticker": ticker,
                    "Quantity": quantity,
                    "Market Price": f"{portfolio.currency} {current_price:,.2f}",
                    "Market Value": market_value, # Keep as number for sorting/charting
                    "Sector": sector
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

    elif view_selection == "Graph":
        st.subheader("Portfolio Graph")
        with st.spinner("Generating graph..."):
            try:
                nodes_data, edges_data = db.get_graph_data(portfolio.name)
                
                nodes = []
                for n in nodes_data:
                    nodes.append(Node(
                        id=n['id'],
                        label=n['label'],
                        size=n['size'],
                        color=n['color'],
                        title=n.get('title', '')
                    ))
                    
                edges = []
                for e in edges_data:
                    edges.append(Edge(
                        source=e['source'],
                        target=e['target'],
                        label=e['label']
                    ))
                
                config = Config(width=800, 
                                height=600, 
                                directed=True, 
                                physics=True, 
                                hierarchical=False,
                                nodeHighlightBehavior=True,
                                highlightColor="#F7A7A6",
                                collapsible=True)
                
                return_value = agraph(nodes=nodes, 
                                      edges=edges, 
                                      config=config)
                                      
                if return_value:
                    st.info(f"Selected Node: {return_value}")
                    
            except Exception as e:
                st.error(f"Error generating graph: {e}")

    # --- PORTFOLIO CHAT ---
    st.markdown("---")
    st.header("Portfolio Chat")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize logs
    if "agent_logs" not in st.session_state:
        st.session_state.agent_logs = []

    col_chat, col_logs = st.columns([1, 1])

    with col_chat:
        st.subheader("Chat")
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask about your portfolio..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                # Capture the current script run context
                ctx = get_script_run_ctx()
                
                # Callback to update logs
                def log_callback(msg):
                    # Attach the context to the current thread (which might be a worker thread)
                    if ctx:
                        add_script_run_ctx(threading.current_thread(), ctx)
                    
                    # Now we can safely access session_state
                    if "agent_logs" in st.session_state:
                        st.session_state.agent_logs.append(msg)
                    
                handler = StatusCallbackHandler(log_callback)
                
                try:
                    agent = get_agent()
                    # Convert session messages to LangChain format
                    history = []
                    for msg in st.session_state.messages:
                        if msg["role"] == "user":
                            history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            history.append(AIMessage(content=msg["content"]))
                    
                    # Invoke agent
                    # We only pass the new message effectively, but LangGraph manages state if we passed the whole history?
                    # Actually, for this simple agent, we pass the list of messages.
                    
                    response = agent.invoke(
                        {"messages": history, "portfolio_id": portfolio.name},
                        config={"callbacks": [handler]}
                    )
                    
                    full_response = response["messages"][-1].content
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.agent_logs.append(f"Error: {e}")

    with col_logs:
        st.subheader("Agent Logs")
        if st.button("Reset Context"):
            st.session_state.messages = []
            st.session_state.agent_logs = []
            st.rerun()
            
        log_container = st.container(height=400)
        with log_container:
            for log in st.session_state.agent_logs:
                st.text(f"• {log}")

