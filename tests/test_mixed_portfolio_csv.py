"""Tests for CSV loading and validation with mixed stock/bond portfolios."""

import pytest
import tempfile
import csv
from pathlib import Path
from pagr.fds.loaders.validator import PositionValidator, ValidationError
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.models.portfolio import Position


class TestPositionValidatorWithBonds:
    """Test position validation supports bonds."""

    def test_validate_stock_position(self):
        """Test validating a stock position."""
        position_dict = {
            "ticker": "AAPL-US",
            "quantity": "100",
            "book_value": "19000.00",
            "security_type": "Common Stock"
        }
        # Should not raise
        try:
            PositionValidator.validate_position(position_dict, row_number=1)
        except ValidationError as e:
            pytest.fail(f"Stock position should be valid: {e}")

    def test_validate_bond_position_with_cusip(self):
        """Test validating a bond position with CUSIP."""
        position_dict = {
            "ticker": "",
            "cusip": "037833AA5",
            "quantity": "500",
            "book_value": "50000.00",
            "security_type": "Corporate Bond"
        }
        # Should not raise
        try:
            PositionValidator.validate_position(position_dict, row_number=1)
        except ValidationError as e:
            pytest.fail(f"Bond position with CUSIP should be valid: {e}")

    def test_validate_bond_position_with_isin(self):
        """Test validating a bond position with ISIN."""
        position_dict = {
            "ticker": "",
            "isin": "US912828Z772",
            "quantity": "300",
            "book_value": "30000.00",
            "security_type": "Treasury Bond"
        }
        # Should not raise
        try:
            PositionValidator.validate_position(position_dict, row_number=1)
        except ValidationError as e:
            pytest.fail(f"Bond position with ISIN should be valid: {e}")

    def test_validate_position_without_identifiers_fails(self):
        """Test that position without identifiers fails."""
        position_dict = {
            "ticker": "",
            "isin": "",
            "cusip": "",
            "quantity": "100",
            "book_value": "10000.00",
            "security_type": "Unknown"
        }
        with pytest.raises(ValidationError) as exc_info:
            PositionValidator.validate_position(position_dict, row_number=1)
        assert "identifier" in str(exc_info.value).lower()

    def test_validate_position_missing_quantity_fails(self):
        """Test that position without quantity fails."""
        position_dict = {
            "ticker": "AAPL-US",
            "quantity": "",
            "book_value": "10000.00",
            "security_type": "Stock"
        }
        with pytest.raises(ValidationError):
            PositionValidator.validate_position(position_dict, row_number=1)

    def test_validate_position_missing_book_value_fails(self):
        """Test that position without book_value fails."""
        position_dict = {
            "ticker": "AAPL-US",
            "quantity": "100",
            "book_value": "",
            "security_type": "Stock"
        }
        with pytest.raises(ValidationError):
            PositionValidator.validate_position(position_dict, row_number=1)


class TestMixedPortfolioLoading:
    """Test loading mixed portfolios from CSV."""

    @pytest.fixture
    def mixed_portfolio_csv(self):
        """Create a mixed portfolio CSV for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["ticker", "isin", "cusip", "quantity", "book_value", "security_type"])
            writer.writeheader()
            writer.writerows([
                {"ticker": "AAPL-US", "isin": "", "cusip": "", "quantity": "100", "book_value": "19000.00", "security_type": "Common Stock"},
                {"ticker": "", "isin": "", "cusip": "037833AA5", "quantity": "500", "book_value": "50000.00", "security_type": "Corporate Bond"},
                {"ticker": "MSFT-US", "isin": "", "cusip": "", "quantity": "50", "book_value": "21000.00", "security_type": "Common Stock"},
                {"ticker": "", "isin": "US912828Z772", "cusip": "", "quantity": "300", "book_value": "30000.00", "security_type": "Treasury Bond"},
            ])
            path = f.name
        yield path
        Path(path).unlink()

    def test_load_mixed_portfolio(self, mixed_portfolio_csv):
        """Test loading a mixed stock/bond portfolio."""
        portfolio = PortfolioLoader.load(mixed_portfolio_csv, portfolio_name="Mixed Portfolio")

        assert portfolio.name == "Mixed Portfolio"
        assert len(portfolio.positions) == 4

        # Verify stocks
        stocks = [p for p in portfolio.positions if p.ticker is not None]
        assert len(stocks) == 2
        assert stocks[0].ticker == "AAPL-US"
        assert stocks[1].ticker == "MSFT-US"

        # Verify bonds
        bonds = [p for p in portfolio.positions if p.ticker is None]
        assert len(bonds) == 2
        assert bonds[0].cusip == "037833AA5"
        assert bonds[1].isin == "US912828Z772"

    def test_load_mixed_portfolio_total_value(self, mixed_portfolio_csv):
        """Test total value calculation for mixed portfolio."""
        portfolio = PortfolioLoader.load(mixed_portfolio_csv, portfolio_name="Mixed Portfolio")

        expected_total = 19000.0 + 50000.0 + 21000.0 + 30000.0
        assert portfolio.total_value == expected_total

    def test_load_mixed_portfolio_positions_have_correct_values(self, mixed_portfolio_csv):
        """Test that all positions load with correct values."""
        portfolio = PortfolioLoader.load(mixed_portfolio_csv, portfolio_name="Mixed Portfolio")

        # Find AAPL position
        aapl = next(p for p in portfolio.positions if p.ticker == "AAPL-US")
        assert aapl.quantity == 100.0
        assert aapl.book_value == 19000.0
        assert aapl.security_type == "Common Stock"

        # Find CUSIP bond
        cusip_bond = next(p for p in portfolio.positions if p.cusip == "037833AA5")
        assert cusip_bond.quantity == 500.0
        assert cusip_bond.book_value == 50000.0
        assert cusip_bond.security_type == "Corporate Bond"

        # Find ISIN bond
        isin_bond = next(p for p in portfolio.positions if p.isin == "US912828Z772")
        assert isin_bond.quantity == 300.0
        assert isin_bond.book_value == 30000.0
        assert isin_bond.security_type == "Treasury Bond"
