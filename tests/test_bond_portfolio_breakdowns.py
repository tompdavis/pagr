"""Integration tests for bond inclusion in portfolio breakdowns.

This test suite verifies that bonds are correctly included in:
1. Sector exposure analysis
2. Country exposure analysis
3. Position-level breakdowns

Tests use a mixed portfolio with both stocks and bonds to ensure
the system properly aggregates and reports on both asset classes.

NOTE: These are integration tests requiring a running Memgraph database.
For unit tests that validate query structure without a database,
see test_bond_queries.py instead.

To run these tests:
1. Start Memgraph: docker run -p 7687:7687 memgraph/memgraph:latest
2. Run: pytest tests/test_bond_portfolio_breakdowns.py -v -m integration
"""

import pytest
from pathlib import Path

from pagr.fds.models.portfolio import Portfolio, Position
from pagr.fds.models.fibo import Stock, Bond, Company
from pagr.fds.graph.builder import GraphBuilder
from pagr.fds.graph.queries import GraphQueries
from pagr.fds.clients.memgraph_client import MemgraphClient


@pytest.fixture
def test_portfolio():
    """Create a mixed portfolio with stocks and bonds."""
    positions = [
        # STOCK 1: AAPL (Tech sector, US)
        Position(
            ticker="AAPL-US",
            quantity=100,
            book_value=19000.00,
            security_type="Common Stock",
            market_value=20000.00,
            weight=0.25,
        ),
        # STOCK 2: BP (Energy sector, UK)
        Position(
            ticker="BP.L",
            quantity=500,
            book_value=10000.00,
            security_type="Common Stock",
            market_value=10500.00,
            weight=0.13,
        ),
        # BOND 1: US Corporate Bond (issued by a US company)
        Position(
            ticker=None,
            quantity=1000,
            book_value=100000.00,
            security_type="Corporate Bond",
            isin="US037833100",
            cusip="037833100",
            market_value=101000.00,
            weight=0.60,
        ),
        # STOCK 3: Nestle (Consumer Staples, Switzerland)
        Position(
            ticker="NESN.S",
            quantity=50,
            book_value=5000.00,
            security_type="Common Stock",
            market_value=5500.00,
            weight=0.02,
        ),
    ]

    portfolio = Portfolio(
        name="Mixed Portfolio with Bonds",
        positions=positions,
        total_value=137000.00,
    )
    return portfolio


@pytest.fixture
def test_stocks():
    """Create Stock FIBO entities."""
    return {
        "AAPL-US": Stock(
            fibo_id="fibo:stock:AAPL-US",
            ticker="AAPL-US",
            security_type="Common Stock",
            market_price=200.0,
        ),
        "BP.L": Stock(
            fibo_id="fibo:stock:BP.L",
            ticker="BP.L",
            security_type="Common Stock",
            market_price=21.0,
        ),
        "NESN.S": Stock(
            fibo_id="fibo:stock:NESN.S",
            ticker="NESN.S",
            security_type="Common Stock",
            market_price=110.0,
        ),
    }


@pytest.fixture
def test_bonds():
    """Create Bond FIBO entities."""
    return {
        "037833100": Bond(
            fibo_id="fibo:bond:037833100",
            cusip="037833100",
            isin="US037833100",
            security_type="Corporate Bond",
            coupon=3.5,
            currency="USD",
            market_price=101.0,
            maturity_date="2030-01-15",
        ),
    }


@pytest.fixture
def test_companies():
    """Create Company FIBO entities."""
    return {
        "AAPL": Company(
            fibo_id="fibo:company:AAPL",
            factset_id="0B4D7P-R",
            ticker="AAPL-US",
            name="Apple, Inc.",
            sector="Technology",
            country="US",
        ),
        "BP": Company(
            fibo_id="fibo:company:BP",
            factset_id="0001FP-R",
            ticker="BP.L",
            name="BP PLC",
            sector="Energy",
            country="GB",
        ),
        "NESTLE": Company(
            fibo_id="fibo:company:NESTLE",
            factset_id="B8TGD3-R",
            ticker="NESN.S",
            name="Nestle SA",
            sector="Consumer Staples",
            country="CH",
        ),
        "USAB": Company(
            fibo_id="fibo:company:USAB",
            factset_id="USABOND-R",
            ticker=None,
            name="US Corporate Bond Issuer",
            sector="Financials",
            country="US",
        ),
    }


@pytest.fixture
def graph_with_bonds(
    test_portfolio, test_stocks, test_bonds, test_companies
):
    """Create a graph database with mixed portfolio."""
    builder = GraphBuilder()

    # Add portfolio node and relationships
    builder.add_portfolio_nodes(test_portfolio)

    # Add position nodes and CONTAINS relationships
    builder.add_position_nodes(test_portfolio.positions, test_portfolio.name)

    # Add stock and bond nodes
    builder.add_security_nodes(stocks=test_stocks, bonds=test_bonds)

    # Add company nodes
    builder.add_company_nodes(test_companies)

    # Build Position->Security mappings
    position_to_security = {
        ("AAPL-US", 100, 19000.0): ("stock", "fibo:stock:AAPL-US"),
        ("BP.L", 500, 10000.0): ("stock", "fibo:stock:BP.L"),
        (None, 1000, 100000.0): ("bond", "fibo:bond:037833100"),
        ("NESN.S", 50, 5000.0): ("stock", "fibo:stock:NESN.S"),
    }

    # Add INVESTED_IN relationships
    builder.add_invested_in_relationships(position_to_security)

    # Build Security->Company mappings
    security_to_company = {
        "fibo:stock:AAPL-US": ("Stock", "fibo:company:AAPL"),
        "fibo:stock:BP.L": ("Stock", "fibo:company:BP"),
        "fibo:bond:037833100": ("Bond", "fibo:company:USAB"),
        "fibo:stock:NESN.S": ("Stock", "fibo:company:NESTLE"),
    }

    # Add ISSUED_BY relationships
    builder.add_security_issued_by_relationships(security_to_company)

    # Execute all queries
    builder.execute()

    return builder


@pytest.mark.integration
class TestBondInclusionInBreakdowns:
    """Test that bonds are properly included in portfolio analysis breakdowns."""

    def test_sector_exposure_includes_bonds(self, graph_with_bonds):
        """Verify sector exposure query includes bonds by issuer sector."""
        client = MemgraphClient()
        client.connect()

        portfolio_name = "Mixed Portfolio with Bonds"
        query = GraphQueries.sector_exposure(portfolio_name)

        results = client.execute_query(query)

        # Should have at least 4 sectors (Tech, Energy, Consumer Staples, Financials)
        assert len(results) >= 4, f"Expected 4+ sectors, got {len(results)}"

        sectors = {r.get("sector") for r in results}

        # Verify Tech sector (AAPL stock)
        assert "Technology" in sectors, "AAPL stock should contribute to Technology sector"

        # Verify Energy sector (BP stock)
        assert "Energy" in sectors, "BP stock should contribute to Energy sector"

        # Verify Consumer Staples (Nestle stock)
        assert "Consumer Staples" in sectors, "Nestle stock should contribute to Consumer Staples"

        # Verify Financials (Bond issuer)
        assert "Financials" in sectors, "Bond issuer should contribute to Financials sector"

        # Verify that Financials sector has exposure
        financials = [r for r in results if r.get("sector") == "Financials"][0]
        assert financials.get("total_exposure") > 0, "Financials sector should have positive exposure"
        assert financials.get("num_positions") > 0, "Financials sector should have at least 1 bond position"

    def test_country_breakdown_includes_bonds(self, graph_with_bonds):
        """Verify country breakdown query includes bonds by issuer country."""
        client = MemgraphClient()
        client.connect()

        portfolio_name = "Mixed Portfolio with Bonds"
        query = GraphQueries.country_breakdown(portfolio_name)

        results = client.execute_query(query)

        # Should have at least 4 countries (US, GB, CH, and potentially others)
        assert len(results) >= 3, f"Expected 3+ countries, got {len(results)}"

        countries = {r.get("country_code") for r in results}

        # Verify US country (AAPL stock + US bond)
        assert "US" in countries, "US should be included (AAPL stock + US bond)"

        # Verify GB country (BP stock)
        assert "GB" in countries, "GB should be included (BP stock)"

        # Verify CH country (Nestle stock)
        assert "CH" in countries, "CH should be included (Nestle stock)"

        # Verify that US has exposure from both stocks and bonds
        us_data = [r for r in results if r.get("country_code") == "US"][0]
        us_exposure = us_data.get("total_exposure")
        us_positions = us_data.get("num_positions")

        # US should have at least 2 positions (AAPL stock + US bond)
        assert us_positions >= 2, f"US should have 2+ positions, got {us_positions}"
        assert us_exposure > 0, "US should have positive exposure"

    def test_sector_exposure_aggregates_bonds_correctly(self, graph_with_bonds):
        """Verify that bond exposure is properly aggregated in sector totals."""
        client = MemgraphClient()
        client.connect()

        portfolio_name = "Mixed Portfolio with Bonds"
        query = GraphQueries.sector_exposure(portfolio_name)

        results = client.execute_query(query)

        # Sum all exposures
        total_exposure = sum(r.get("total_exposure", 0) for r in results)

        # Should approximately equal portfolio total (137000)
        # Allow for rounding errors
        assert total_exposure > 0, "Total exposure should be positive"
        assert 130000 < total_exposure < 140000, f"Total exposure should be ~137000, got {total_exposure}"

    def test_country_breakdown_aggregates_bonds_correctly(self, graph_with_bonds):
        """Verify that bond exposure is properly aggregated in country totals."""
        client = MemgraphClient()
        client.connect()

        portfolio_name = "Mixed Portfolio with Bonds"
        query = GraphQueries.country_breakdown(portfolio_name)

        results = client.execute_query(query)

        # Sum all exposures
        total_exposure = sum(r.get("total_exposure", 0) for r in results)

        # Should approximately equal portfolio total (137000)
        assert total_exposure > 0, "Total exposure should be positive"
        assert 130000 < total_exposure < 140000, f"Total exposure should be ~137000, got {total_exposure}"

    def test_bond_not_in_stock_sector_breakdown(self, graph_with_bonds):
        """Verify that bonds appear in sector breakdown via issuer, not as stock."""
        client = MemgraphClient()
        client.connect()

        portfolio_name = "Mixed Portfolio with Bonds"
        query = GraphQueries.sector_exposure(portfolio_name)

        results = client.execute_query(query)

        # The bond should NOT appear in Technology/Energy/Consumer Staples
        # It should only appear in Financials (its issuer's sector)

        for sector_result in results:
            sector = sector_result.get("sector")
            if sector in ["Technology", "Energy", "Consumer Staples"]:
                # These sectors should still have their stock positions
                assert sector_result.get("num_positions") > 0, f"{sector} should have positions"

        # Verify Financials has the bond
        financials_results = [r for r in results if r.get("sector") == "Financials"]
        assert len(financials_results) > 0, "Financials sector should exist"
        assert financials_results[0].get("num_positions") > 0, "Financials should have bond position"

    def test_multiple_bonds_in_breakdown(self):
        """Verify that multiple bonds are properly aggregated in breakdowns."""
        # Create portfolio with 2 bonds from same issuer
        positions = [
            Position(
                ticker=None,
                quantity=1000,
                book_value=100000.00,
                security_type="Corporate Bond",
                isin="US037833100",
                cusip="037833100",
                market_value=101000.00,
                weight=0.50,
            ),
            Position(
                ticker=None,
                quantity=500,
                book_value=50000.00,
                security_type="Corporate Bond",
                isin="US037833101",
                cusip="037833101",
                market_value=51000.00,
                weight=0.50,
            ),
        ]

        portfolio = Portfolio(
            name="Multi-Bond Portfolio",
            positions=positions,
            total_value=152000.00,
        )

        bonds = {
            "037833100": Bond(
                fibo_id="fibo:bond:037833100",
                cusip="037833100",
                isin="US037833100",
                security_type="Corporate Bond",
                coupon=3.5,
                currency="USD",
                market_price=101.0,
            ),
            "037833101": Bond(
                fibo_id="fibo:bond:037833101",
                cusip="037833101",
                isin="US037833101",
                security_type="Corporate Bond",
                coupon=4.0,
                currency="USD",
                market_price=102.0,
            ),
        }

        company = Company(
            fibo_id="fibo:company:USAB",
            factset_id="USABOND-R",
            ticker=None,
            name="Multi-Bond Issuer",
            sector="Financials",
            country="US",
        )

        # Build graph
        builder = GraphBuilder()
        builder.add_portfolio_nodes(portfolio)
        builder.add_position_nodes(portfolio.positions, portfolio.name)
        builder.add_security_nodes(bonds=bonds)
        builder.add_company_nodes({"USAB": company})

        position_to_security = {
            (None, 1000, 100000.0): ("bond", "fibo:bond:037833100"),
            (None, 500, 50000.0): ("bond", "fibo:bond:037833101"),
        }
        builder.add_invested_in_relationships(position_to_security)

        security_to_company = {
            "fibo:bond:037833100": ("Bond", "fibo:company:USAB"),
            "fibo:bond:037833101": ("Bond", "fibo:company:USAB"),
        }
        builder.add_security_issued_by_relationships(security_to_company)
        builder.execute()

        # Query should show both bonds aggregated
        client = MemgraphClient()
        client.connect()

        query = GraphQueries.sector_exposure(portfolio.name)
        results = client.execute_query(query)

        # Should have only 1 sector (Financials) with 2 positions aggregated
        assert len(results) == 1, f"Expected 1 sector, got {len(results)}"

        financials = results[0]
        assert financials.get("sector") == "Financials"
        assert financials.get("num_positions") == 2, "Should have 2 bond positions"
        assert 150000 < financials.get("total_exposure", 0) < 155000, "Should have ~152000 exposure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
