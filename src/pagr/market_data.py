import yfinance as yf
import pandas as pd
import requests
import re
import urllib.parse
from typing import List, Dict, Any, Optional

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

def fetch_company_metadata(ticker: str) -> Dict[str, Any]:
    """
    Fetches Sector (Yahoo) and LEI/Legal Name (GLEIF).
    """
    metadata = {
        "sector": "Unknown",
        "lei": None,
        "legal_name": f"Unknown ({ticker})"
    }

    try:
        # 1. Yahoo Finance (Sector & ISIN)
        yf_ticker = clean_ticker(ticker)
        stock = yf.Ticker(yf_ticker)
        
        # Note: yfinance can be flaky. If 'info' fails, we handle it.
        try:
            info = stock.info
            metadata['sector'] = info.get('sector', 'Unknown')
            isin = stock.isin
            # Fallback to shortName if longName is missing
            name = info.get('longName') or info.get('shortName')
        except Exception:
            # Fallback if info fails
            info = {}
            isin = None
            name = None
        
        # 2. GLEIF (LEI via ISIN)
        lei_found = False
        if isin and isin != '-' and re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin):
            url = f"https://api.gleif.org/api/v1/lei-records?filter[isin]={isin}"
            try:
                resp = requests.get(url).json()
                if resp.get('data'):
                    record = resp['data'][0]['attributes']
                    metadata['lei'] = record['lei']
                    metadata['legal_name'] = record['entity']['legalName']['name']
                    lei_found = True
            except Exception:
                pass

        # 3. GLEIF (Fallback: Fuzzy Name Search)
        if not lei_found and name:
            safe_name = urllib.parse.quote(name)
            url = f"https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]={safe_name}"
            try:
                resp = requests.get(url).json()
                if resp.get('data'):
                    record = resp['data'][0]['attributes']
                    metadata['lei'] = record['lei']
                    metadata['legal_name'] = record['entity']['legalName']['name']
            except Exception:
                pass

    except Exception as e:
        print(f"Metadata fetch issue for {ticker}: {e}")

    return metadata
