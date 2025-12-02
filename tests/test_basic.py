"""Basic tests for PAGR components."""

import pytest
from pagr.fds.models.portfolio import Portfolio, Position
from pagr.session_manager import SessionManager, PipelineStatistics


class TestPortfolioModel:
    """Test Portfolio and Position models from fds_api."""

    def test_position_creation(self):
        """Test creating a Position instance."""
        pos = Position(
            ticker="AAPL-US",
            quantity=100.0,
            book_value=19000.0,
            security_type="Common Stock"
        )
        assert pos.ticker == "AAPL-US"
        assert pos.quantity == 100.0
        assert pos.book_value == 19000.0

    def test_portfolio_creation(self):
        """Test creating a Portfolio instance."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=19000.0),
            Position(ticker="MSFT-US", quantity=50.0, book_value=21000.0),
        ]
        portfolio = Portfolio(name="Test Portfolio", positions=positions)
        assert portfolio.name == "Test Portfolio"
        assert len(portfolio.positions) == 2

    def test_portfolio_total_value(self):
        """Test portfolio total book value calculation."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=10000.0),
            Position(ticker="MSFT-US", quantity=50.0, book_value=10000.0),
        ]
        portfolio = Portfolio(name="Test", positions=positions)
        portfolio.calculate_weights()
        expected_value = 20000.0
        assert portfolio.total_value == expected_value


class TestSessionManager:
    """Test Streamlit session state management."""

    def test_session_initialization(self):
        """Test session state initialization."""
        # Simulate Streamlit session
        import streamlit as st
        SessionManager.initialize()
        assert st.session_state.portfolio is None
        assert st.session_state.graph_built is False

    def test_session_portfolio_operations(self):
        """Test setting and getting portfolio from session."""
        import streamlit as st
        SessionManager.initialize()

        portfolio = Portfolio(name="Test", positions=[])
        stats = PipelineStatistics()

        SessionManager.set_portfolio(portfolio, stats)
        retrieved = SessionManager.get_portfolio()

        assert retrieved is not None
        assert retrieved.name == "Test"


class TestPipelineStatistics:
    """Test pipeline statistics data class."""

    def test_statistics_creation(self):
        """Test creating statistics instance."""
        stats = PipelineStatistics(
            positions_loaded=5,
            companies_enriched=3,
            executives_enriched=2
        )
        assert stats.positions_loaded == 5
        assert stats.companies_enriched == 3
        assert stats.executives_enriched == 2

    def test_statistics_error_tracking(self):
        """Test error tracking in statistics."""
        stats = PipelineStatistics()
        stats.errors.append("Test error 1")
        stats.errors.append("Test error 2")

        assert len(stats.errors) == 2
        assert "Test error 1" in stats.errors
