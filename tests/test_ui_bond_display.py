"""Tests for UI display logic with bond support."""

import pytest
import pandas as pd
from pagr.fds.models.portfolio import Position
from pagr.ui.tabular import _get_security_description


class TestSecurityDescriptionDisplay:
    """Test _get_security_description helper function for UI display."""

    def test_display_stock_with_ticker(self):
        """Test that stocks display their ticker."""
        pos = Position(
            ticker="AAPL-US",
            quantity=100.0,
            book_value=19000.0,
            security_type="Common Stock"
        )
        description = _get_security_description(pos)
        assert description == "AAPL-US"

    def test_display_bond_with_cusip(self):
        """Test that bonds display CUSIP with (Bond) label."""
        pos = Position(
            cusip="037833AA5",
            quantity=500.0,
            book_value=50000.0,
            security_type="Corporate Bond"
        )
        description = _get_security_description(pos)
        assert description == "037833AA5 (Bond)"
        assert "(Bond)" in description

    def test_display_bond_with_isin(self):
        """Test that bonds display ISIN with (Bond) label when CUSIP unavailable."""
        pos = Position(
            isin="US912828Z772",
            quantity=300.0,
            book_value=30000.0,
            security_type="Treasury Bond"
        )
        description = _get_security_description(pos)
        assert description == "US912828Z772 (Bond)"
        assert "(Bond)" in description

    def test_display_prefers_cusip_over_isin(self):
        """Test that CUSIP is preferred over ISIN in display."""
        pos = Position(
            isin="US912828Z772",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0,
            security_type="Bond"
        )
        description = _get_security_description(pos)
        assert "037833AA5" in description
        assert "US912828Z772" not in description

    def test_display_prefers_stock_ticker_over_cusip(self):
        """Test that stock ticker is displayed even if CUSIP present."""
        pos = Position(
            ticker="AAPL-US",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0,
            security_type="Mixed"
        )
        description = _get_security_description(pos)
        assert description == "AAPL-US"
        assert "(Bond)" not in description

    def test_display_stock_with_multiple_identifiers_prefers_ticker(self):
        """Test that ticker is preferred for display when all identifiers present."""
        pos = Position(
            ticker="AAPL-US",
            isin="US037833AA56",
            cusip="037833AA5",
            quantity=100.0,
            book_value=10000.0,
            security_type="Stock"
        )
        # Ticker should be displayed first (highest priority)
        description = _get_security_description(pos)
        assert description == "AAPL-US"
        assert "(Bond)" not in description


class TestDataFrameDisplay:
    """Test DataFrame display logic for mixed portfolios."""

    def test_positions_dataframe_with_stocks(self):
        """Test positions DataFrame with stock positions."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=19000.0, security_type="Common Stock"),
            Position(ticker="MSFT-US", quantity=50.0, book_value=21000.0, security_type="Common Stock"),
        ]

        # Simulate UI display logic
        positions_data = []
        for pos in positions:
            positions_data.append({
                "Security": _get_security_description(pos),
                "Type": pos.security_type,
                "Quantity": pos.quantity,
                "Book Value": f"${pos.book_value:,.2f}",
            })

        df = pd.DataFrame(positions_data)

        assert len(df) == 2
        assert df.loc[0, "Security"] == "AAPL-US"
        assert df.loc[1, "Security"] == "MSFT-US"
        assert all(df["Type"] == "Common Stock")

    def test_positions_dataframe_with_bonds(self):
        """Test positions DataFrame with bond positions."""
        positions = [
            Position(cusip="037833AA5", quantity=500.0, book_value=50000.0, security_type="Corporate Bond"),
            Position(isin="US912828Z772", quantity=300.0, book_value=30000.0, security_type="Treasury Bond"),
        ]

        # Simulate UI display logic
        positions_data = []
        for pos in positions:
            positions_data.append({
                "Security": _get_security_description(pos),
                "Type": pos.security_type,
                "Quantity": pos.quantity,
                "Book Value": f"${pos.book_value:,.2f}",
            })

        df = pd.DataFrame(positions_data)

        assert len(df) == 2
        assert "037833AA5 (Bond)" in df.loc[0, "Security"]
        assert "US912828Z772 (Bond)" in df.loc[1, "Security"]
        assert df.loc[0, "Type"] == "Corporate Bond"
        assert df.loc[1, "Type"] == "Treasury Bond"

    def test_positions_dataframe_mixed(self):
        """Test positions DataFrame with mixed stocks and bonds."""
        positions = [
            Position(ticker="AAPL-US", quantity=100.0, book_value=19000.0, security_type="Common Stock"),
            Position(cusip="037833AA5", quantity=500.0, book_value=50000.0, security_type="Corporate Bond"),
            Position(ticker="MSFT-US", quantity=50.0, book_value=21000.0, security_type="Common Stock"),
            Position(isin="US912828Z772", quantity=300.0, book_value=30000.0, security_type="Treasury Bond"),
        ]

        # Simulate UI display logic
        positions_data = []
        for pos in positions:
            positions_data.append({
                "Security": _get_security_description(pos),
                "Type": pos.security_type,
                "Quantity": pos.quantity,
                "Book Value": f"${pos.book_value:,.2f}",
            })

        df = pd.DataFrame(positions_data)

        assert len(df) == 4
        assert df.loc[0, "Security"] == "AAPL-US"
        assert "(Bond)" in df.loc[1, "Security"]
        assert df.loc[2, "Security"] == "MSFT-US"
        assert "(Bond)" in df.loc[3, "Security"]

    def test_sector_positions_with_null_tickers(self):
        """Test that sector positions handle NULL tickers for bonds correctly."""
        # Simulate query results from sector_positions query
        # which returns NULL ticker for bonds
        sector_pos_data = [
            {"ticker": "AAPL-US", "company": "Apple Inc.", "quantity": 100.0, "market_value": 15000.0, "weight": 20.0},
            {"ticker": None, "company": "Apple Inc. Bond", "quantity": 500.0, "market_value": 50000.0, "weight": 67.0},  # Bond
        ]

        sector_pos_df = pd.DataFrame(sector_pos_data)

        # Simulate UI display logic: rename and handle NULL tickers
        display_df = sector_pos_df.copy()
        display_df = display_df.rename(columns={"ticker": "Security"})

        # Handle NULL tickers by showing "Bond"
        display_df['Security'] = display_df.apply(
            lambda row: row['Security'] if pd.notnull(row['Security']) and row['Security'] != '' else 'Bond',
            axis=1
        )

        assert display_df.loc[0, "Security"] == "AAPL-US"
        assert display_df.loc[1, "Security"] == "Bond"

    def test_country_positions_with_null_tickers(self):
        """Test that country positions handle NULL tickers for bonds correctly."""
        # Simulate query results from country_positions query
        country_pos_data = [
            {"ticker": "AAPL-US", "company": "Apple Inc.", "quantity": 100.0, "market_value": 15000.0, "weight": 20.0},
            {"ticker": None, "company": "US Treasury", "quantity": 300.0, "market_value": 30000.0, "weight": 40.0},  # Bond
        ]

        country_pos_df = pd.DataFrame(country_pos_data)

        # Simulate UI display logic
        display_df = country_pos_df.copy()
        display_df = display_df.rename(columns={"ticker": "Security"})

        # Handle NULL tickers by showing "Bond"
        display_df['Security'] = display_df.apply(
            lambda row: row['Security'] if pd.notnull(row['Security']) and row['Security'] != '' else 'Bond',
            axis=1
        )

        assert display_df.loc[0, "Security"] == "AAPL-US"
        assert display_df.loc[1, "Security"] == "Bond"


class TestTableHeightPadding:
    """Test that table padding logic works with mixed asset types."""

    def test_pad_dataframe_with_mixed_securities(self):
        """Test that dataframe padding works correctly with mixed securities."""
        from pagr.ui.tabular import _pad_dataframe_to_height

        # Create a small dataframe with mixed securities
        data = [
            {"Security": "AAPL-US", "Type": "Stock", "Quantity": 100},
            {"Security": "037833AA5 (Bond)", "Type": "Bond", "Quantity": 500},
        ]
        df = pd.DataFrame(data)

        # Pad to 10 rows
        padded_df = _pad_dataframe_to_height(df, max_rows=10)

        assert len(padded_df) == 10
        assert padded_df.loc[0, "Security"] == "AAPL-US"
        assert padded_df.loc[1, "Security"] == "037833AA5 (Bond)"
        # Rest should be empty rows
        assert padded_df.loc[9, "Security"] == ""
