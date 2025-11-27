import yfinance as yf
import pandas as pd
from typing import List, Dict, Any

def clean_ticker(ticker: str) -> str:
    """Replaces dots with dashes for Yahoo Finance compatibility."""
    return ticker.replace('.', '-')

def get_current_prices(tickers: List[str]) -> pd.Series:
    """
    Fetches the last close price for a list of tickers.
    Returns a pandas Series indexed by ticker.
    """
    if not tickers:
        return pd.Series()

    cleaned_tickers = [clean_ticker(t) for t in tickers]
    
    # Fetch data for 1 day
    # yfinance.download returns a MultiIndex DataFrame if multiple tickers are passed
    # We want the 'Close' column.
    # group_by='ticker' makes it easier to handle
    try:
        data = yf.download(cleaned_tickers, period="1d", progress=False, group_by='ticker')
        
        # Extract close prices
        # If multiple tickers, data columns are (Ticker, PriceType)
        # If single ticker, data columns are PriceType
        
        prices = {}
        if len(cleaned_tickers) == 1:
            ticker = cleaned_tickers[0]
            # Handle single ticker case
            if not data.empty:
                 prices[tickers[0]] = data['Close'].iloc[-1]
        else:
            for i, ticker in enumerate(cleaned_tickers):
                original_ticker = tickers[i]
                try:
                    # Access the column for the specific ticker
                    if ticker in data.columns.levels[0]:
                         prices[original_ticker] = data[ticker]['Close'].iloc[-1]
                except KeyError:
                    print(f"Could not find data for {ticker}")
                    prices[original_ticker] = 0.0
                    
        return pd.Series(prices)

    except Exception as e:
        print(f"Error fetching prices: {e}")
        return pd.Series()

def get_sector_info(tickers: List[str]) -> Dict[str, str]:
    """
    Fetches sector information for a list of tickers.
    Returns a dictionary mapping ticker to sector.
    """
    sectors = {}
    for ticker in tickers:
        cleaned = clean_ticker(ticker)
        try:
            info = yf.Ticker(cleaned).info
            sectors[ticker] = info.get('sector', 'Unknown')
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            sectors[ticker] = 'Unknown'
            
    return sectors

def validate_ticker(ticker: str) -> bool:
    """
    Validates if a ticker exists using Yahoo Finance.
    Returns True if valid, False otherwise.
    """
    cleaned = clean_ticker(ticker)
    try:
        # yfinance doesn't have a cheap 'exists' check. 
        # We can try to fetch info or history. 
        # .info can be slow and sometimes unreliable.
        # Let's try fetching 1 day of history for validation.
        data = yf.download(cleaned, period="1d", progress=False)
        return not data.empty
    except Exception:
        return False
