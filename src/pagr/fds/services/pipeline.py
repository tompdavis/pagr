"""ETL pipeline orchestrator for portfolio graph database.

Coordinates loading, enriching, and building graph from portfolio data.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.clients.factset_client import (
    FactSetClient,
    FactSetAuthenticationError,
    FactSetPermissionError,
    FactSetNotFoundError,
)
from pagr.fds.enrichers.company_enricher import CompanyEnricher
from pagr.fds.enrichers.bond_enricher import BondEnricher
from pagr.fds.enrichers.relationship_enricher import RelationshipEnricher
from pagr.fds.graph.builder import GraphBuilder
from pagr.fds.models.portfolio import Portfolio, Position
from pagr.fds.models.fibo import Company, Country, Executive, Stock, Bond

logger = logging.getLogger(__name__)


@dataclass
class PipelineStatistics:
    """Statistics from pipeline execution."""

    portfolios_loaded: int = 0
    positions_loaded: int = 0
    stocks_enriched: int = 0
    bonds_enriched: int = 0
    companies_enriched: int = 0
    companies_failed: int = 0
    bonds_failed: int = 0
    executives_enriched: int = 0
    countries_enriched: int = 0
    graph_nodes_created: int = 0
    graph_relationships_created: int = 0
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message.

        Args:
            error: Error message
        """
        self.errors.append(error)

    def to_dict(self) -> Dict:
        """Convert to dictionary.

        Returns:
            Dict representation of statistics
        """
        return {
            "portfolios_loaded": self.portfolios_loaded,
            "positions_loaded": self.positions_loaded,
            "stocks_enriched": self.stocks_enriched,
            "bonds_enriched": self.bonds_enriched,
            "companies_enriched": self.companies_enriched,
            "companies_failed": self.companies_failed,
            "bonds_failed": self.bonds_failed,
            "executives_enriched": self.executives_enriched,
            "countries_enriched": self.countries_enriched,
            "graph_nodes_created": self.graph_nodes_created,
            "graph_relationships_created": self.graph_relationships_created,
            "total_errors": len(self.errors),
        }


class ETLPipeline:
    """Main ETL pipeline orchestrator."""

    def __init__(
        self,
        factset_client: FactSetClient,
        portfolio_loader: PortfolioLoader,
        graph_builder: GraphBuilder,
    ):
        """Initialize ETL pipeline.

        Args:
            factset_client: FactSet API client
            portfolio_loader: Portfolio loader
            graph_builder: Graph builder
        """
        self.factset_client = factset_client
        self.portfolio_loader = portfolio_loader
        self.graph_builder = graph_builder
        self.stats = PipelineStatistics()
        logger.info("Initialized ETL pipeline")

    def load_portfolio(self, portfolio_file: str, portfolio_name: str = None) -> Optional[Portfolio]:
        """Load portfolio from file.

        Args:
            portfolio_file: Path to portfolio CSV file
            portfolio_name: Optional name for portfolio (defaults to filename stem)

        Returns:
            Portfolio instance or None if load fails
        """
        try:
            logger.info(f"Loading portfolio from {portfolio_file}")
            portfolio = self.portfolio_loader.load(portfolio_file, portfolio_name=portfolio_name)

            self.stats.portfolios_loaded = 1
            self.stats.positions_loaded = len(portfolio.positions)
            logger.info(
                f"Loaded portfolio '{portfolio.name}' with {len(portfolio.positions)} positions"
            )
            return portfolio

        except Exception as e:
            error_msg = f"Failed to load portfolio: {str(e)}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)
            return None

    def enrich_positions(
        self, positions: List[Position]
    ) -> Tuple[
        Dict[str, Stock],
        Dict[str, Bond],
        Dict[str, Company],
        Dict[str, Country],
        Dict[str, Executive],
    ]:
        """Enrich positions with FactSet data, supporting both stocks and bonds.

        Separates positions into stocks (with ticker) and bonds (with ISIN/CUSIP),
        enriching each through the appropriate FactSet API and enricher.

        Args:
            positions: List of positions to enrich

        Returns:
            Tuple of (stocks dict, bonds dict, companies dict, countries dict, executives dict)
        """
        stocks: Dict[str, Stock] = {}
        bonds: Dict[str, Bond] = {}
        companies: Dict[str, Company] = {}
        countries: Dict[str, Country] = {}
        executives: Dict[str, Executive] = {}

        logger.info(f"Enriching {len(positions)} positions with FactSet data")

        company_enricher = CompanyEnricher(self.factset_client)
        bond_enricher = BondEnricher(self.factset_client)
        relationship_enricher = RelationshipEnricher(self.factset_client)

        for idx, position in enumerate(positions):
            primary_id_type, primary_id = position.get_primary_identifier()
            logger.debug(
                f"[{idx+1}/{len(positions)}] Enriching position: {primary_id_type}={primary_id}"
            )

            # DEBUG: Log routing decision for every position
            logger.debug(
                f"  Position routing: ticker='{position.ticker}', cusip='{position.cusip}', "
                f"isin='{position.isin}', security_type='{position.security_type}'"
            )

            try:
                # Route to stock or bond enrichment based on identifier type
                if position.ticker:
                    # Stock enrichment (existing flow)
                    logger.debug(f"  → Routing to STOCK enrichment (ticker present)")
                    self._enrich_stock_position(
                        position,
                        primary_id,
                        company_enricher,
                        relationship_enricher,
                        stocks,
                        companies,
                        countries,
                        executives,
                    )
                else:
                    # Bond enrichment (new flow)
                    logger.debug(f"  → Routing to BOND enrichment (no ticker, using {primary_id_type})")
                    self._enrich_bond_position(
                        position,
                        bond_enricher,
                        bonds,
                        companies,
                        countries,
                    )

            except Exception as e:
                # Catch-all for unexpected errors
                error_msg = (
                    f"Unexpected error enriching {primary_id_type}={primary_id}: {str(e)}"
                )
                logger.error(error_msg)
                self.stats.add_error(error_msg)
                if position.ticker:
                    self.stats.companies_failed += 1
                else:
                    self.stats.bonds_failed += 1

        logger.info(
            f"Enrichment complete: "
            f"{self.stats.stocks_enriched} stocks, "
            f"{self.stats.bonds_enriched} bonds, "
            f"{self.stats.companies_enriched} companies, "
            f"{self.stats.companies_failed} company failures, "
            f"{self.stats.bonds_failed} bond failures"
        )
        return stocks, bonds, companies, countries, executives

    def _enrich_stock_position(
        self,
        position: Position,
        ticker: str,
        company_enricher: CompanyEnricher,
        relationship_enricher: RelationshipEnricher,
        stocks: Dict[str, Stock],
        companies: Dict[str, Company],
        countries: Dict[str, Country],
        executives: Dict[str, Executive],
    ) -> None:
        """Enrich a single stock position.

        Args:
            position: Position object
            ticker: Stock ticker
            company_enricher: CompanyEnricher instance
            relationship_enricher: RelationshipEnricher instance
            stocks: Dict to accumulate Stock objects
            companies: Dict to accumulate Company objects
            countries: Dict to accumulate Country objects
            executives: Dict to accumulate Executive objects
        """
        try:
            # Enrich company data
            company = company_enricher.enrich_company(ticker)
            if company:
                companies[ticker] = company
                self.stats.companies_enriched += 1
                logger.debug(f"  Enriched company: {company.name}")

                # Create Stock FIBO entity
                stock = Stock(
                    fibo_id=f"fibo:stock:{ticker}",
                    ticker=ticker,
                    security_type=position.security_type or "Common Stock",
                    isin=position.isin,
                    cusip=position.cusip,
                    sedol=None,
                    market_price=None,  # Will be filled by enrich_prices
                )
                stocks[position.cusip] = stock
                self.stats.stocks_enriched += 1
                logger.debug(f"  Created Stock entity for {ticker}")

                # Enrich executives for this company
                try:
                    company_executives = company_enricher.enrich_executives(
                        company.fibo_id
                    )
                    for exec_obj in company_executives:
                        executives[exec_obj.fibo_id] = exec_obj
                        self.stats.executives_enriched += 1
                    logger.debug(f"  Enriched {len(company_executives)} executives")
                except Exception as e:
                    logger.warning(f"  Failed to enrich executives for {ticker}: {e}")

                # Enrich geography data
                if company.country:
                    try:
                        country_data = relationship_enricher.enrich_geography(
                            company.fibo_id, company.country
                        )
                        if country_data and len(country_data) > 0:
                            for rel in country_data:
                                if rel.target_fibo_id not in countries:
                                    country = Country(
                                        fibo_id=rel.target_fibo_id,
                                        name=company.country,
                                        iso_code=company.country[:2]
                                        if company.country
                                        else "XX",
                                    )
                                    countries[company.country] = country
                                    self.stats.countries_enriched += 1
                            logger.debug(f"  Enriched geography")
                    except Exception as e:
                        logger.warning(
                            f"  Failed to enrich geography for {ticker}: {e}"
                        )
            else:
                self.stats.companies_failed += 1
                logger.warning(f"Failed to enrich company for {ticker}")

        except (FactSetAuthenticationError, FactSetPermissionError) as e:
            # Critical errors
            error_msg = f"Failed to enrich stock {ticker}: {str(e)}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)
            self.stats.companies_failed += 1

        except FactSetNotFoundError as e:
            # Not found errors
            logger.warning(f"Ticker not found: {ticker} ({str(e)})")
            self.stats.companies_failed += 1

    def _enrich_bond_position(
        self,
        position: Position,
        bond_enricher: BondEnricher,
        bonds: Dict[str, Bond],
        companies: Dict[str, Company],
        countries: Dict[str, Country],
    ) -> None:
        """Enrich a single bond position.

        Args:
            position: Position object (bond)
            bond_enricher: BondEnricher instance
            bonds: Dict to accumulate Bond objects
            companies: Dict to accumulate Company objects
            countries: Dict to accumulate Country objects
        """
        try:
            # Enrich bond data
            bond = bond_enricher.enrich_bond(position.cusip, position.isin)
            if bond:
                # Use primary identifier as key for bonds
                primary_id_type, primary_id = position.get_primary_identifier()

                # Do NOT use book_value as fallback - show N/A in UI if no market price from API
                if bond.market_price is None:
                    logger.debug(f"  No market price available from FactSet for {primary_id_type}={primary_id}, will display as N/A")

                bonds[primary_id] = bond
                self.stats.bonds_enriched += 1
                logger.debug(f"  Enriched bond: {primary_id_type}={primary_id}")

                # Try to resolve and enrich issuer company
                try:
                    issuer_company = bond_enricher.resolve_issuer(
                        position.cusip, position.isin
                    )
                    if issuer_company:
                        # Use issuer name as key
                        if issuer_company.name not in companies:
                            companies[issuer_company.name] = issuer_company
                            self.stats.companies_enriched += 1
                            logger.debug(
                                f"  Resolved bond issuer: {issuer_company.name}"
                            )

                            # Try to enrich geography for issuer if available
                            if issuer_company.country:
                                try:
                                    iso_code = issuer_company.country[:2].upper()
                                    if iso_code not in countries:
                                        country = Country(
                                            fibo_id=f"fibo:country:{iso_code}",
                                            name=issuer_company.country,
                                            iso_code=iso_code,
                                        )
                                        countries[iso_code] = country
                                        self.stats.countries_enriched += 1
                                except Exception as e:
                                    logger.debug(
                                        f"  Could not enrich issuer geography: {e}"
                                    )
                        else:
                            logger.debug(
                                f"  Issuer already enriched: {issuer_company.name}"
                            )
                    else:
                        logger.debug(f"  Could not resolve issuer for bond")
                except Exception as e:
                    logger.warning(f"  Failed to enrich bond issuer: {e}")

            else:
                self.stats.bonds_failed += 1
                primary_id_type, primary_id = position.get_primary_identifier()
                logger.warning(f"Failed to enrich bond {primary_id_type}={primary_id}")

        except Exception as e:
            error_msg = f"Error enriching bond: {str(e)}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)
            self.stats.bonds_failed += 1

    def build_graph(
        self,
        portfolio: Portfolio,
        stocks: Dict[str, Stock],
        bonds: Dict[str, Bond],
        companies: Dict[str, Company],
        countries: Dict[str, Country],
        executives: Dict[str, Executive],
    ) -> List[str]:
        """Build graph nodes and relationships for mixed stock/bond portfolio.

        New graph schema:
        - Position -[CONTAINS]-> Portfolio
        - Position -[INVESTED_IN]-> Stock/Bond
        - Stock/Bond -[ISSUED_BY]-> Company
        - Company -[HEADQUARTERED_IN]-> Country

        Args:
            portfolio: Portfolio instance
            stocks: Dictionary of enriched stocks
            bonds: Dictionary of enriched bonds
            companies: Dictionary of enriched companies
            countries: Dictionary of enriched countries
            executives: Dictionary of enriched executives

        Returns:
            List of all Cypher statements
        """
        logger.info("Building graph nodes and relationships")

        try:
            # Add portfolio node
            self.graph_builder.add_portfolio_nodes(portfolio)
            self.stats.graph_nodes_created += 1

            # Add position nodes and CONTAINS relationships
            self.graph_builder.add_position_nodes(portfolio.positions, portfolio.name)
            self.stats.graph_nodes_created += len(portfolio.positions)
            self.stats.graph_relationships_created += len(portfolio.positions)

            # Add security nodes (stocks and bonds)
            if stocks or bonds:
                self.graph_builder.add_security_nodes(stocks, bonds)
                self.stats.graph_nodes_created += len(stocks) + len(bonds)

            # Add company nodes
            if companies:
                self.graph_builder.add_company_nodes(companies)
                self.stats.graph_nodes_created += len(companies)

            # Add country nodes
            if countries:
                self.graph_builder.add_country_nodes(countries)
                self.stats.graph_nodes_created += len(countries)

            # Add executive nodes
            if executives:
                self.graph_builder.add_executive_nodes(executives)
                self.stats.graph_nodes_created += len(executives)

            # Build Position -> Security mappings for INVESTED_IN relationships
            # Maps: (position_ticker, position_quantity, position_book_value) -> (security_type, security_fibo_id)
            # NOTE: Using CUSIP for matching instead of ticker because:
            # - Tickers can be ambiguous (same ticker on different exchanges)
            # - CUSIP is unique identifier provided by FactSet enrichment
            # - Future: Consider switching to ISIN for better support of non-North American portfolios
            position_to_security: Dict[tuple, Tuple[str, str]] = {}
            for position in portfolio.positions:
                # Use CUSIP as the primary lookup key for stocks (not ticker)
                # CUSIP is more reliable than ticker and matches how stocks dict is keyed
                if position.cusip and position.cusip in stocks:
                    # Stock position - use CUSIP to lookup in stocks dict
                    stock_fibo_id = stocks[position.cusip].fibo_id
                    position_to_security[(position.ticker, position.quantity, position.book_value)] = ("stock", stock_fibo_id)
                elif position.cusip or position.isin:
                    # Bond position - look up by CUSIP/ISIN, but use position properties as key
                    primary_id_type, primary_id = position.get_primary_identifier()
                    if primary_id in bonds:
                        bond_fibo_id = bonds[primary_id].fibo_id
                        # Use (ticker, quantity, book_value) as unique position key
                        pos_key = (position.ticker or "", position.quantity, position.book_value)
                        position_to_security[pos_key] = ("bond", bond_fibo_id)

            # Add INVESTED_IN relationships (Position -> Security)
            if position_to_security:
                self.graph_builder.add_invested_in_relationships(position_to_security, portfolio.name)
                self.stats.graph_relationships_created += len(position_to_security)

            # Build Security -> Company mappings for ISSUED_BY relationships
            security_to_company: Dict[str, Tuple[str, str]] = {}

            # Stocks -> Companies
            for ticker, stock in stocks.items():
                if ticker in companies:
                    company_fibo_id = companies[ticker].fibo_id
                    security_to_company[stock.fibo_id] = ("stock", company_fibo_id)

            # Bonds -> Companies (by issuer)
            for bond_id, bond in bonds.items():
                # Find issuer company - check if it's in companies dict by issuer name
                for company_name, company in companies.items():
                    # If this company was created from bond enrichment, use it
                    # We match by name since bond issuers are identified by name
                    if company.name and bond_id not in security_to_company:
                        # This is a simplified approach - in reality you'd want better matching
                        # For now, we assume each bond has one issuer that's in companies
                        security_to_company[bond.fibo_id] = ("bond", company.fibo_id)
                        break

            # Add ISSUED_BY relationships (Security -> Company)
            if security_to_company:
                self.graph_builder.add_security_issued_by_relationships(
                    security_to_company
                )
                self.stats.graph_relationships_created += len(security_to_company)

            # Add HEADQUARTERED_IN relationships (company -> country)
            company_to_country = {}
            for company_id, company in companies.items():
                if company.country:
                    # Try to find ISO code from countries dict
                    iso_code = None
                    for country_name, country_obj in countries.items():
                        if country_name.lower() == company.country.lower():
                            iso_code = country_obj.iso_code
                            break
                    if not iso_code:
                        # Fallback: use first 2 characters of country name
                        iso_code = company.country[:2].upper()
                    company_to_country[company.fibo_id] = iso_code

            if company_to_country:
                self.graph_builder.add_headquartered_in_relationships(company_to_country)
                self.stats.graph_relationships_created += len(company_to_country)

            # Get all statements
            statements = self.graph_builder.get_all_statements()
            logger.info(
                f"Graph building complete: "
                f"{self.stats.graph_nodes_created} nodes, "
                f"{self.stats.graph_relationships_created} relationships"
            )
            return statements

        except Exception as e:
            error_msg = f"Failed to build graph: {str(e)}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)
            return []

    def enrich_prices(self, portfolio: Portfolio) -> None:
        """Enrich portfolio positions with market prices.

        Handles both stock prices (by ticker) and bond prices (by ISIN/CUSIP).

        Args:
            portfolio: Portfolio to enrich
        """
        logger.info(f"Enriching prices for {len(portfolio.positions)} positions")

        try:
            # Separate stocks and bonds
            stock_positions = [p for p in portfolio.positions if p.ticker]
            bond_positions = [p for p in portfolio.positions if p.cusip or p.isin]

            price_map = {}

            # Enrich stock prices
            if stock_positions:
                try:
                    tickers = [p.ticker for p in stock_positions]
                    logger.debug(f"Fetching prices for {len(tickers)} stocks")
                    response = self.factset_client.get_last_close_prices(tickers)

                    if "data" in response:
                        for item in response["data"]:
                            ticker = item.get("requestId")
                            price = item.get("price")
                            date_str = item.get("date")

                            if ticker and price is not None:
                                # If we already have a price for this ticker, check if newer
                                if ticker in price_map:
                                    existing_date, _ = price_map[ticker]
                                    if not date_str or date_str > existing_date:
                                        price_map[ticker] = (date_str, float(price))
                                else:
                                    price_map[ticker] = (date_str, float(price))
                except Exception as e:
                    logger.warning(f"Failed to fetch stock prices: {e}")
                    self.stats.add_error(f"Stock price enrichment failed: {e}")

            # Enrich bond prices using Formula API with batch processing
            if bond_positions:
                try:
                    logger.debug(f"Fetching prices for {len(bond_positions)} bonds via Formula API")

                    # Group bonds by CUSIP (preferred) and ISIN
                    cusip_positions = [p for p in bond_positions if p.cusip]
                    isin_positions = [p for p in bond_positions if not p.cusip and p.isin]

                    # Process CUSIP bonds in batches (up to 10 per request)
                    if cusip_positions:
                        batch_size = 10
                        for i in range(0, len(cusip_positions), batch_size):
                            batch = cusip_positions[i : i + batch_size]
                            cusips = [p.cusip for p in batch]
                            try:
                                response = self.factset_client.get_bond_prices_formula_api(cusips)

                                # Extract prices from Formula API response
                                data = response.get("data", {})
                                for position in batch:
                                    if position.cusip in data:
                                        price = data[position.cusip].get("price")
                                        if price is not None:
                                            price_map[position.cusip] = (None, float(price))
                                            logger.debug(f"Got Formula API price for {position.cusip}: {price}")
                            except Exception as e:
                                logger.warning(f"Formula API batch call failed for CUSIPs: {e}. Falling back to individual Global Prices calls.")
                                # Fallback: try Global Prices API for this batch
                                for position in batch:
                                    try:
                                        response = self.factset_client.get_bond_prices([position.cusip], id_type="CUSIP")
                                        if "data" in response and len(response["data"]) > 0:
                                            bond_data = response["data"][0]
                                            price = bond_data.get("price")
                                            if price is not None:
                                                price_map[position.cusip] = (None, float(price))
                                    except Exception as e2:
                                        logger.debug(f"Could not fetch price for CUSIP {position.cusip}: {e2}")

                    # Process ISIN bonds individually (less common)
                    for position in isin_positions:
                        try:
                            response = self.factset_client.get_bond_prices([position.isin], id_type="ISIN")
                            if "data" in response and len(response["data"]) > 0:
                                bond_data = response["data"][0]
                                price = bond_data.get("price")
                                if price is not None:
                                    price_map[position.isin] = (None, float(price))
                        except Exception as e:
                            logger.debug(f"Could not fetch price for ISIN {position.isin}: {e}")

                except Exception as e:
                    logger.warning(f"Failed to enrich bond prices: {e}")
                    self.stats.add_error(f"Bond price enrichment failed: {e}")

            # Update positions with prices
            updated_count = 0
            for position in portfolio.positions:
                # Get the identifier to look up in price_map
                if position.ticker and position.ticker in price_map:
                    _, price = price_map[position.ticker]
                    position.market_value = position.quantity * price
                    updated_count += 1
                elif position.cusip or position.isin:
                    primary_id_type, primary_id = position.get_primary_identifier()
                    if primary_id in price_map:
                        _, price = price_map[primary_id]
                        position.market_value = position.quantity * price
                        updated_count += 1

            logger.info(f"Updated market values for {updated_count}/{len(portfolio.positions)} positions")

            # Recalculate weights
            portfolio.calculate_weights()

        except Exception as e:
            error_msg = f"Unexpected error enriching prices: {e}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)

    def execute(self, portfolio_file: str, portfolio_name: str = None) -> Tuple[Optional[Portfolio], List[str], PipelineStatistics]:
        """Execute full ETL pipeline for mixed stock/bond portfolios.

        Args:
            portfolio_file: Path to portfolio CSV file
            portfolio_name: Optional name for portfolio (defaults to filename stem)

        Returns:
            Tuple of (Portfolio, Cypher statements, statistics)
        """
        logger.info("=" * 70)
        logger.info("Starting ETL Pipeline")
        logger.info("=" * 70)

        # Step 1: Load portfolio with explicit name
        portfolio = self.load_portfolio(portfolio_file, portfolio_name=portfolio_name)
        if not portfolio:
            logger.error("Pipeline failed: Could not load portfolio")
            return None, [], self.stats

        # Step 2: Enrich prices
        self.enrich_prices(portfolio)

        # Step 3: Enrich positions (stocks, bonds, companies, countries, executives)
        stocks, bonds, companies, countries, executives = self.enrich_positions(
            portfolio.positions
        )

        # Step 4: Build graph with new schema
        statements = self.build_graph(
            portfolio, stocks, bonds, companies, countries, executives
        )

        logger.info("=" * 70)
        logger.info("ETL Pipeline Complete")
        logger.info("=" * 70)
        logger.info(f"Statistics: {self.stats.to_dict()}")

        return portfolio, statements, self.stats

    def reset(self) -> None:
        """Reset pipeline state for new execution."""
        self.stats = PipelineStatistics()
        self.graph_builder.clear()
        logger.debug("Pipeline state reset")
