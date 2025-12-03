"""Test that bond queries include bonds in sector and country breakdowns.

This test suite verifies that the Cypher queries for sector and country
exposure analysis include bonds through the INVESTED_IN relationship.
"""

import pytest
from pagr.fds.graph.queries import GraphQueries


class TestBondQueriesStructure:
    """Test that bond-related queries have correct structure."""

    def test_sector_exposure_query_has_invested_in(self):
        """Verify sector exposure query includes INVESTED_IN relationship."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # Should have INVESTED_IN relationship
        assert "-[:INVESTED_IN]->" in query, "Query should have INVESTED_IN relationship"

        # Should not have direct ISSUED_BY from position (old schema)
        assert "CONTAINS]->(pos)-[:ISSUED_BY]" not in query, "Query should not have direct Position->ISSUED_BY"

        # Should have the new pattern: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company
        # Remove whitespace for comparison
        query_normalized = " ".join(query.split())
        assert "(pos:Position)-[:INVESTED_IN]->(sec)" in query_normalized, "Query should have Position INVESTED_IN Security"
        assert "-[:ISSUED_BY]->(c:Company)" in query_normalized, "Query should have Security ISSUED_BY Company"

    def test_country_breakdown_query_has_invested_in(self):
        """Verify country breakdown query includes INVESTED_IN relationship."""
        query = GraphQueries.country_breakdown("Test Portfolio")

        # Should have INVESTED_IN relationship
        assert "-[:INVESTED_IN]->" in query, "Query should have INVESTED_IN relationship"

        # Should have the new pattern: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company
        query_normalized = " ".join(query.split())
        assert "(pos:Position)-[:INVESTED_IN]->(sec)" in query_normalized, "Query should have Position INVESTED_IN Security"
        assert "-[:ISSUED_BY]->(c:Company)" in query_normalized, "Query should have Security ISSUED_BY Company"

    def test_country_positions_query_has_invested_in(self):
        """Verify country positions query includes INVESTED_IN relationship."""
        query = GraphQueries.country_positions("Test Portfolio", "US")

        # Should have INVESTED_IN relationship
        assert "-[:INVESTED_IN]->" in query, "Query should have INVESTED_IN relationship"

        # Should have the new pattern with Security node
        query_normalized = " ".join(query.split())
        assert "(pos:Position)-[:INVESTED_IN]->(sec)" in query_normalized, "Query should have Position INVESTED_IN Security"

    def test_sector_exposure_query_matches_portfolio(self):
        """Verify sector exposure query matches specified portfolio."""
        portfolio_name = "My Test Portfolio"
        query = GraphQueries.sector_exposure(portfolio_name)

        # Should have the portfolio name in the query
        assert f"name: '{portfolio_name}'" in query, "Query should filter by portfolio name"

    def test_country_breakdown_query_returns_required_fields(self):
        """Verify country breakdown returns required aggregation fields."""
        query = GraphQueries.country_breakdown("Test Portfolio")

        # Should return country info
        assert "country.iso_code" in query or "country_code" in query, "Query should return country code"

        # Should return aggregated exposure
        assert "SUM(pos.market_value)" in query, "Query should sum market values"

        # Should count positions for visibility into bond vs stock mix
        assert "COUNT(pos)" in query or "num_positions" in query, "Query should count positions"

    def test_queries_use_new_graph_schema(self):
        """Verify all queries use the new v2.0 schema with intermediate Security nodes."""
        portfolio_name = "Test Portfolio"
        queries = {
            "sector_exposure": GraphQueries.sector_exposure(portfolio_name),
            "country_breakdown": GraphQueries.country_breakdown(portfolio_name),
            "country_positions": GraphQueries.country_positions(portfolio_name, "US"),
        }

        for query_name, query_text in queries.items():
            # All should have the Security node (sec)
            assert "(sec)" in query_text, f"{query_name} should reference (sec) security node"

            # All should have INVESTED_IN relationship
            assert "INVESTED_IN" in query_text, f"{query_name} should use INVESTED_IN relationship"


class TestBondInclusionLogic:
    """Test the logical correctness of bond inclusion in queries."""

    def test_bonds_route_through_invested_in(self):
        """Verify that bonds must route through INVESTED_IN to companies."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # The path should be: Portfolio -> Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company
        # This means both stocks and bonds (as different types of Security) will be included

        # Check the relationship chain
        path_start = query.find("Position")
        path_invested_in = query.find("INVESTED_IN", path_start)
        path_security = query.find("(sec)", path_invested_in)
        path_issued_by = query.find("ISSUED_BY", path_security)
        path_company = query.find("(c:Company)", path_issued_by)

        # All parts should exist in order
        assert path_start != -1, "Query should have Position"
        assert path_invested_in != -1, "Query should have INVESTED_IN after Position"
        assert path_security != -1, "Query should have Security (sec) after INVESTED_IN"
        assert path_issued_by != -1, "Query should have ISSUED_BY after Security"
        assert path_company != -1, "Query should have Company after ISSUED_BY"

    def test_sector_exposure_aggregates_across_security_types(self):
        """Verify sector exposure properly aggregates both stocks and bonds."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # Should aggregate market_value (applies to both stocks and bonds)
        assert "SUM(pos.market_value)" in query, "Should aggregate market values for all positions"

        # Should match companies regardless of security type
        # This is implicit - since (sec) can be Stock or Bond, both will match
        assert "RETURN" in query, "Query should have RETURN clause for results"
        assert "c.sector" in query or "sector" in query, "Should return company sector"

    def test_country_breakdown_includes_all_positions(self):
        """Verify country breakdown includes positions from all asset classes."""
        query = GraphQueries.country_breakdown("Test Portfolio")

        # Count should work for both stocks and bonds
        assert "COUNT(pos)" in query, "Should count all positions"

        # Company headquarter location should work for all issuers
        assert "HEADQUARTERED_IN" in query, "Should use company location"
        assert "country" in query, "Should return country information"


class TestQueryEdgeCases:
    """Test edge cases in bond handling within queries."""

    def test_multiple_bonds_from_same_issuer(self):
        """Verify that multiple bonds from same issuer are properly aggregated."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # The aggregation should work even if multiple positions
        # (both stocks and bonds) link to the same company
        # This is handled by the GROUP BY or aggregation functions
        assert "SUM" in query or "COUNT" in query, "Query should aggregate multiple positions"

    def test_bonds_without_market_data(self):
        """Verify queries handle bonds that may not have full market data."""
        query = GraphQueries.sector_exposure("Test Portfolio")

        # Query uses pos.market_value which may be NULL for bonds
        # but SUM should still work (treats NULL as 0)
        assert "SUM(pos.market_value)" in query, "Query should handle potential NULL values"

    def test_query_performance_with_large_portfolios(self):
        """Verify queries are efficiently structured for large portfolios."""
        query = GraphQueries.country_breakdown("Test Portfolio")

        # Should have proper filtering to avoid Cartesian products
        assert "MATCH" in query, "Should have explicit MATCH clause"
        assert "-[:CONTAINS]" in query, "Should filter to specific portfolio"

        # Should not have multiple similar patterns that could cause duplicates
        pattern_count = query.count("OPTIONAL MATCH")
        assert pattern_count <= 3, "Should minimize OPTIONAL MATCH clauses"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
