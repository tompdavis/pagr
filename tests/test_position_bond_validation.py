"""Tests for Position model validation with bond support."""

import pytest
from pydantic import ValidationError
from pagr.fds.models.portfolio import Position, Portfolio


class TestPositionIdentifierValidation:
    """Test Position model validator for identifier requirements."""

    def test_position_with_ticker_only(self):
        """Test creating a Position with only ticker (stock)."""
        pos = Position(
            ticker="AAPL-US",
            quantity=100.0,
            book_value=19000.0,
            security_type="Common Stock"
        )
        assert pos.ticker == "AAPL-US"
        assert pos.isin is None
        assert pos.cusip is None
        assert pos.get_primary_identifier() == ("ticker", "AAPL-US")

    def test_position_with_isin_only(self):
        """Test creating a Position with only ISIN (bond)."""
        pos = Position(
            isin="US912828Z772",
            quantity=500.0,
            book_value=50000.0,
            security_type="Treasury Bond"
        )
        assert pos.ticker is None
        assert pos.isin == "US912828Z772"
        assert pos.cusip is None
        assert pos.get_primary_identifier() == ("isin", "US912828Z772")

    def test_position_with_cusip_only(self):
        """Test creating a Position with only CUSIP (bond)."""
        pos = Position(
            cusip="037833AA5",
            quantity=300.0,
            book_value=30000.0,
            security_type="Corporate Bond"
        )
        assert pos.ticker is None
        assert pos.isin is None
        assert pos.cusip == "037833AA5"
        assert pos.get_primary_identifier() == ("cusip", "037833AA5")

    def test_position_without_any_identifier_fails(self):
        """Test that Position without any identifier raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Position(
                quantity=100.0,
                book_value=10000.0
            )
        assert "Must provide at least one identifier" in str(exc_info.value)

    def test_position_with_empty_identifiers_fails(self):
        """Test that Position with empty identifier strings fails."""
        with pytest.raises(ValidationError) as exc_info:
            Position(
                ticker="",
                isin="",
                cusip="",
                quantity=100.0,
                book_value=10000.0
            )
        assert "Must provide at least one identifier" in str(exc_info.value)

    def test_position_identifier_priority_cusip_over_isin(self):
        """Test that CUSIP is preferred over ISIN."""
        pos = Position(
            isin="US912828Z772",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0
        )
        id_type, id_value = pos.get_primary_identifier()
        assert id_type == "cusip"
        assert id_value == "037833AA5"

    def test_position_identifier_priority_isin_over_ticker(self):
        """Test that ISIN is preferred over ticker."""
        pos = Position(
            ticker="AAPL-US",
            isin="US912828Z772",
            quantity=100.0,
            book_value=10000.0
        )
        id_type, id_value = pos.get_primary_identifier()
        assert id_type == "isin"
        assert id_value == "US912828Z772"

    def test_position_identifier_priority_cusip_over_all(self):
        """Test that CUSIP is preferred over both ISIN and ticker."""
        pos = Position(
            ticker="AAPL-US",
            isin="US912828Z772",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0
        )
        id_type, id_value = pos.get_primary_identifier()
        assert id_type == "cusip"
        assert id_value == "037833AA5"

    def test_position_with_all_identifiers_uses_cusip_priority(self):
        """Test that when all identifiers present, CUSIP is chosen."""
        pos = Position(
            ticker="AAPL-US",
            isin="US912828Z772",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0,
            security_type="Mixed"
        )
        assert pos.get_primary_identifier() == ("cusip", "037833AA5")


class TestMixedPortfolioCreation:
    """Test creating portfolios with mixed stocks and bonds."""

    def test_portfolio_with_stocks_only(self):
        """Test creating portfolio with only stocks."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=19000.0),
            Position(ticker="MSFT-US", quantity=50.0, book_value=21000.0),
        ]
        portfolio = Portfolio(name="Stocks Only", positions=positions)
        assert len(portfolio.positions) == 2
        assert all(pos.ticker is not None for pos in portfolio.positions)

    def test_portfolio_with_bonds_only(self):
        """Test creating portfolio with only bonds."""
        positions = [
            Position(cusip="037833AA5", quantity=500.0, book_value=50000.0),
            Position(isin="US912828Z772", quantity=300.0, book_value=30000.0),
        ]
        portfolio = Portfolio(name="Bonds Only", positions=positions)
        assert len(portfolio.positions) == 2
        assert all(pos.ticker is None for pos in portfolio.positions)
        assert portfolio.positions[0].cusip is not None
        assert portfolio.positions[1].isin is not None

    def test_portfolio_with_mixed_stocks_and_bonds(self):
        """Test creating portfolio with both stocks and bonds."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=19000.0),
            Position(cusip="037833AA5", quantity=500.0, book_value=50000.0),
            Position(ticker="MSFT-US", quantity=50.0, book_value=21000.0),
            Position(isin="US912828Z772", quantity=300.0, book_value=30000.0),
        ]
        portfolio = Portfolio(name="Mixed Portfolio", positions=positions)
        assert len(portfolio.positions) == 4

        # Verify stocks
        stocks = [p for p in portfolio.positions if p.ticker is not None]
        assert len(stocks) == 2

        # Verify bonds
        bonds = [p for p in portfolio.positions if p.ticker is None]
        assert len(bonds) == 2

    def test_portfolio_total_value_with_mixed_assets(self):
        """Test that total_value is calculated correctly for mixed portfolios."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=10000.0),
            Position(cusip="037833AA5", quantity=500.0, book_value=50000.0),
        ]
        portfolio = Portfolio(name="Mixed", positions=positions)
        portfolio.calculate_weights()
        assert portfolio.total_value == 60000.0
        assert portfolio.positions[0].weight == pytest.approx(10000.0 / 60000.0 * 100, abs=0.1)
        assert portfolio.positions[1].weight == pytest.approx(50000.0 / 60000.0 * 100, abs=0.1)
