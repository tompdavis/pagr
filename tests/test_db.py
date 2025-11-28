import pytest
from pagr import db
from pagr.portfolio import Portfolio, Position
from unittest.mock import patch, MagicMock

@pytest.fixture
def sample_portfolio():
    pos1 = Position(ticker="AAPL", quantity=10, book_value=1500.0)
    pos2 = Position(ticker="MSFT", quantity=5, book_value=1000.0)
    return Portfolio(name="Test Portfolio", currency="USD", last_updated="2024-01-01", positions=[pos1, pos2])

def test_memgraph_connection():
    """Verifies that we can connect to Memgraph."""
    try:
        driver = db.get_driver()
        driver.verify_connectivity()
        driver.close()
    except Exception as e:
        pytest.fail(f"Could not connect to Memgraph: {e}")

def test_load_and_view_portfolio(sample_portfolio):
    """
    Tests loading a portfolio into Memgraph and retrieving the view.
    WARNING: This test modifies the database!
    """
    # Mock fetch_company_metadata to avoid external API calls during test
    with patch('pagr.db.fetch_company_metadata') as mock_fetch:
        mock_fetch.return_value = {
            "sector": "Technology",
            "lei": "TEST_LEI",
            "legal_name": "Test Company"
        }
        
        try:
            # 1. Load
            db.load_portfolio(sample_portfolio)
            
            # 2. View
            view = db.get_portfolio_view(sample_portfolio.name)
            
            assert len(view) == 2
            
            tickers = sorted([p['ticker'] for p in view])
            assert tickers == ["AAPL", "MSFT"]
            
            # Check sector (should be what we mocked)
            assert view[0]['sector'] == "Technology"
            
        except Exception as e:
            pytest.fail(f"Database operation failed: {e}")
