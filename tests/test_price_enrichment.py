"""Test price enrichment and weight calculation."""

import pytest
from unittest.mock import MagicMock, patch
from pagr.fds.models.portfolio import Portfolio, Position
from pagr.fds.services.pipeline import ETLPipeline
from pagr.fds.clients.factset_client import FactSetClient

@pytest.fixture
def sample_portfolio():
    p = Portfolio(name="Test Portfolio")
    p.add_position(Position(ticker="AAPL-US", quantity=10, book_value=1000.0))
    p.add_position(Position(ticker="MSFT-US", quantity=20, book_value=2000.0))
    return p

def test_calculate_weights_with_market_value(sample_portfolio):
    """Test weight calculation when market values are present."""
    # Set market values
    # AAPL: 10 * 150 = 1500
    # MSFT: 20 * 100 = 2000
    # Total: 3500
    # AAPL weight: 1500/3500 = 42.857%
    # MSFT weight: 2000/3500 = 57.142%
    
    sample_portfolio.positions[0].market_value = 1500.0
    sample_portfolio.positions[1].market_value = 2000.0
    
    sample_portfolio.calculate_weights()
    
    assert sample_portfolio.total_value == 3500.0
    assert abs(sample_portfolio.positions[0].weight - 42.857) < 0.01
    assert abs(sample_portfolio.positions[1].weight - 57.142) < 0.01

def test_calculate_weights_fallback_to_book_value(sample_portfolio):
    """Test fallback to book value when no market values are present."""
    # Total book value: 3000
    # AAPL: 1000/3000 = 33.33%
    # MSFT: 2000/3000 = 66.66%
    
    sample_portfolio.calculate_weights()
    
    assert sample_portfolio.total_value == 3000.0
    assert abs(sample_portfolio.positions[0].weight - 33.333) < 0.01
    assert abs(sample_portfolio.positions[1].weight - 66.666) < 0.01

def test_enrich_prices():
    """Test enrich_prices method in ETLPipeline."""
    mock_client = MagicMock(spec=FactSetClient)
    mock_client.get_last_close_prices.return_value = {
        "data": [
            {"requestId": "AAPL-US", "price": 150.0, "date": "2025-12-01"},
            {"requestId": "MSFT-US", "price": 100.0, "date": "2025-12-01"}
        ]
    }
    
    pipeline = ETLPipeline(
        factset_client=mock_client,
        portfolio_loader=MagicMock(),
        graph_builder=MagicMock()
    )
    
    portfolio = Portfolio(name="Test Portfolio")
    portfolio.add_position(Position(ticker="AAPL-US", quantity=10, book_value=1000.0))
    portfolio.add_position(Position(ticker="MSFT-US", quantity=20, book_value=2000.0))
    
    pipeline.enrich_prices(portfolio)
    
    # Verify client call
    mock_client.get_last_close_prices.assert_called_once_with(["AAPL-US", "MSFT-US"])
    
    # Verify market values updated
    # AAPL: 10 * 150 = 1500
    # MSFT: 20 * 100 = 2000
    assert portfolio.positions[0].market_value == 1500.0
    assert portfolio.positions[1].market_value == 2000.0
    
    # Verify weights recalculated
    assert portfolio.total_value == 3500.0
    assert abs(portfolio.positions[0].weight - 42.857) < 0.01
