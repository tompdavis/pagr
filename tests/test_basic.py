import pytest
from pagr.portfolio import Portfolio
from pagr.market_data import clean_ticker
from pathlib import Path

def test_clean_ticker():
    assert clean_ticker("BRK.B") == "BRK-B"
    assert clean_ticker("AAPL") == "AAPL"

def test_portfolio_loading(tmp_path):
    # Create a dummy portfolio file
    p_file = tmp_path / "test.pagr"
    p_file.write_text("""
    {
        "portfolio_name": "Test Portfolio",
        "currency": "USD",
        "positions": [
            { "ticker": "AAPL", "quantity": 10, "book_value": 1500.0 }
        ]
    }
    """)
    
    p = Portfolio.from_file(p_file)
    assert p.name == "Test Portfolio"
    assert len(p.positions) == 1
    assert p.positions[0].ticker == "AAPL"
    assert p.positions[0].quantity == 10

def test_portfolio_get_tickers(tmp_path):
    p_file = tmp_path / "test.pagr"
    p_file.write_text("""
    {
        "portfolio_name": "Test",
        "positions": [
            { "ticker": "AAPL", "quantity": 10, "book_value": 100 },
            { "ticker": "MSFT", "quantity": 5, "book_value": 200 }
        ]
    }
    """)
    p = Portfolio.from_file(p_file)
    tickers = p.get_tickers()
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert len(tickers) == 2
