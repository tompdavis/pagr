"""Tests for graph queries with bond support."""

import pytest
from unittest.mock import Mock
from pagr.fds.graph.queries import GraphQueries, QueryService


class TestBondGraphQueries:
    """Test Cypher queries include bonds correctly."""

    def test_sector_exposure_query_includes_invested_in(self):
        """Test that sector_exposure query uses new INVESTED_IN relationship."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # Should include INVESTED_IN hop for new schema
        assert "INVESTED_IN" in query
        # Should NOT have direct Position -> Company connection
        assert "-[:ISSUED_BY]" in query
        # Verify the relationship chain
        assert "Position" in query
        assert "Company" in query

    def test_country_breakdown_query_includes_invested_in(self):
        """Test that country_breakdown query uses new INVESTED_IN relationship."""
        query = GraphQueries.country_breakdown("Test Portfolio")

        # Should include INVESTED_IN hop for new schema
        assert "INVESTED_IN" in query
        # Should have ISSUED_BY for Security -> Company
        assert "-[:ISSUED_BY]" in query
        # Should query Country nodes
        assert "Country" in query

    def test_sector_positions_query_handles_bond_tickers(self):
        """Test that sector_positions query returns NULL for bond tickers."""
        query = GraphQueries.sector_positions("Test Portfolio", "Technology")

        # Should use CASE statement to handle NULL tickers for bonds
        assert "CASE WHEN" in query
        assert "sec:Stock" in query
        assert "sec.ticker" in query
        # Should include sector filter
        assert "sector:" in query or "sector =" in query

    def test_country_positions_query_handles_bond_tickers(self):
        """Test that country_positions query returns NULL for bond tickers."""
        query = GraphQueries.country_positions("Test Portfolio", "US")

        # Should use CASE statement to handle NULL tickers for bonds
        assert "CASE WHEN" in query
        assert "sec:Stock" in query
        assert "sec.ticker" in query
        # Should filter by country
        assert "iso_code:" in query or "iso_code =" in query

    def test_sector_exposure_query_returns_correct_fields(self):
        """Test that sector_exposure query returns expected fields."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # Should return these fields
        assert "sector" in query or "Sector" in query
        assert "total_exposure" in query or "SUM" in query
        assert "total_weight" in query
        assert "num_positions" in query


class TestQueryServiceWithBonds:
    """Test QueryService methods with bond data."""

    def setup_method(self):
        """Setup mock graph client for testing."""
        self.mock_client = Mock()
        self.query_service = QueryService(self.mock_client)

    def test_sector_exposure_with_bonds(self):
        """Test sector_exposure query returns bonds grouped by issuer sector."""
        # Mock results that include bonds
        mock_records = [
            {"sector": "Technology", "total_exposure": 50000.0, "total_weight": 35.0, "num_positions": 3},
            {"sector": "Finance", "total_exposure": 35000.0, "total_weight": 25.0, "num_positions": 2},
        ]
        self.mock_client.execute_query.return_value = mock_records

        result = self.query_service.sector_exposure("Mixed Portfolio")

        assert len(result.records) == 2
        assert result.records[0]["sector"] == "Technology"
        assert result.records[0]["total_exposure"] == 50000.0

    def test_country_breakdown_with_bonds(self):
        """Test country_breakdown query includes bonds."""
        mock_records = [
            {"country_code": "US", "country": "United States", "total_exposure": 80000.0, "total_weight": 60.0, "num_positions": 5},
            {"country_code": "GB", "country": "United Kingdom", "total_exposure": 40000.0, "total_weight": 30.0, "num_positions": 2},
        ]
        self.mock_client.execute_query.return_value = mock_records

        result = self.query_service.country_breakdown("Mixed Portfolio")

        assert len(result.records) == 2
        assert result.records[0]["country_code"] == "US"
        assert result.records[0]["total_exposure"] == 80000.0

    def test_sector_positions_with_bonds_returns_null_ticker(self):
        """Test sector_positions query returns NULL ticker for bonds."""
        mock_records = [
            {"ticker": "AAPL-US", "company": "Apple Inc.", "quantity": 100.0, "market_value": 15000.0, "weight": 20.0},
            {"ticker": None, "company": "Apple Inc.", "quantity": 500.0, "market_value": 50000.0, "weight": 67.0},  # Bond
            {"ticker": "MSFT-US", "company": "Microsoft Corp", "quantity": 50.0, "market_value": 25000.0, "weight": 33.0},
        ]
        self.mock_client.execute_query.return_value = mock_records

        result = self.query_service.sector_positions("Mixed Portfolio", "Technology")

        # Verify records include both stocks and bonds
        stocks = [r for r in result.records if r["ticker"] is not None]
        bonds = [r for r in result.records if r["ticker"] is None]

        assert len(stocks) == 2
        assert len(bonds) == 1
        assert bonds[0]["market_value"] == 50000.0

    def test_country_positions_with_bonds_returns_null_ticker(self):
        """Test country_positions query returns NULL ticker for bonds."""
        mock_records = [
            {"ticker": "AAPL-US", "company": "Apple Inc.", "quantity": 100.0, "market_value": 15000.0, "weight": 20.0},
            {"ticker": None, "company": "US Treasury", "quantity": 300.0, "market_value": 30000.0, "weight": 40.0},  # Bond
        ]
        self.mock_client.execute_query.return_value = mock_records

        result = self.query_service.country_positions("Mixed Portfolio", "US")

        assert len(result.records) == 2
        # Verify mixed results with stocks and bonds
        stocks = [r for r in result.records if r["ticker"] is not None]
        bonds = [r for r in result.records if r["ticker"] is None]
        assert len(stocks) == 1
        assert len(bonds) == 1


class TestQueryResultFormatting:
    """Test formatting query results for display."""

    def test_format_sector_exposure_table(self):
        """Test formatting sector exposure results as table."""
        mock_records = [
            {"sector": "Technology", "total_exposure": 50000.0, "total_weight": 35.0, "num_positions": 3},
            {"sector": "Finance", "total_exposure": 35000.0, "total_weight": 25.0, "num_positions": 2},
        ]

        from pagr.fds.graph.queries import QueryResult
        result = QueryResult(
            query_name="sector_exposure",
            cypher="MATCH...",
            records=mock_records
        )

        # Mock graph client
        mock_client = Mock()
        query_service = QueryService(mock_client)

        # Format result as table
        table = query_service.format_result_table(result)

        assert "Technology" in table
        assert "Finance" in table
        assert "50000" in table
        assert "35000" in table

    def test_format_mixed_sector_positions_table(self):
        """Test formatting sector positions with both stocks and bonds."""
        mock_records = [
            {"ticker": "AAPL-US", "company": "Apple Inc.", "quantity": 100.0, "market_value": 15000.0, "weight": 20.0},
            {"ticker": None, "company": "Apple Inc. Bond", "quantity": 500.0, "market_value": 50000.0, "weight": 67.0},
        ]

        from pagr.fds.graph.queries import QueryResult
        result = QueryResult(
            query_name="sector_positions",
            cypher="MATCH...",
            records=mock_records
        )

        mock_client = Mock()
        query_service = QueryService(mock_client)

        # Format result as table
        table = query_service.format_result_table(result)

        assert "AAPL-US" in table
        assert "Apple Inc" in table
        assert "15000" in table
        assert "50000" in table
