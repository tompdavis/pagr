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
    companies_enriched: int = 0
    companies_failed: int = 0
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
            "companies_enriched": self.companies_enriched,
            "companies_failed": self.companies_failed,
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

    def load_portfolio(self, portfolio_file: str) -> Optional[Portfolio]:
        """Load portfolio from file.

        Args:
            portfolio_file: Path to portfolio CSV file

        Returns:
            Portfolio instance or None if load fails
        """
        try:
            logger.info(f"Loading portfolio from {portfolio_file}")
            portfolio = self.portfolio_loader.load(portfolio_file)

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
    ) -> Tuple[Dict[str, Company], Dict[str, Country], Dict[str, Executive]]:
        """Enrich positions with FactSet data.

        Args:
            positions: List of positions to enrich

        Returns:
            Tuple of (companies dict, countries dict, executives dict)
        """
        companies: Dict[str, Company] = {}
        countries: Dict[str, Country] = {}
        executives: Dict[str, Executive] = {}

        logger.info(f"Enriching {len(positions)} positions with FactSet data")

        company_enricher = CompanyEnricher(self.factset_client)
        relationship_enricher = RelationshipEnricher(self.factset_client)

        for idx, position in enumerate(positions):
            ticker = position.ticker
            logger.debug(f"[{idx+1}/{len(positions)}] Enriching position: {ticker}")

            try:
                # Enrich company data
                company = company_enricher.enrich_company(ticker)
                if company:
                    companies[ticker] = company
                    self.stats.companies_enriched += 1
                    logger.debug(f"  Enriched company: {company.name}")

                    # Enrich executives for this company
                    try:
                        company_executives = company_enricher.enrich_executives(company.fibo_id)
                        for exec_obj in company_executives:
                            executives[exec_obj.fibo_id] = exec_obj
                            self.stats.executives_enriched += 1
                        logger.debug(
                            f"  Enriched {len(company_executives)} executives"
                        )
                    except Exception as e:
                        logger.warning(f"  Failed to enrich executives for {ticker}: {e}")

                    # Enrich geography data
                    if company.country:
                        try:
                            country_data = relationship_enricher.enrich_geography(
                                company.fibo_id, company.country
                            )
                            if country_data and len(country_data) > 0:
                                # country_data is a list of Relationship objects,
                                # but we need Country objects. Extract from target
                                for rel in country_data:
                                    if rel.target_fibo_id not in countries:
                                        # Create a Country object from relationship
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
                error_msg = f"Failed to enrich {ticker}: {str(e)}"
                logger.error(error_msg)
                self.stats.add_error(error_msg)
                self.stats.companies_failed += 1

            except FactSetNotFoundError as e:
                # Not found errors
                logger.warning(f"Ticker not found: {ticker} ({str(e)})")
                self.stats.companies_failed += 1

            except Exception as e:
                # Other errors
                error_msg = f"Unexpected error enriching {ticker}: {str(e)}"
                logger.error(error_msg)
                self.stats.add_error(error_msg)
                self.stats.companies_failed += 1

        logger.info(
            f"Enrichment complete: "
            f"{self.stats.companies_enriched} companies, "
            f"{self.stats.companies_failed} failed"
        )
        return companies, countries, executives

    def build_graph(
        self,
        portfolio: Portfolio,
        companies: Dict[str, Company],
        countries: Dict[str, Country],
        executives: Dict[str, Executive],
    ) -> List[str]:
        """Build graph nodes and relationships.

        Args:
            portfolio: Portfolio instance
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

            # Add ISSUED_BY relationships (position -> company)
            position_to_company = {pos.ticker: companies[pos.ticker].fibo_id
                                 for pos in portfolio.positions
                                 if pos.ticker in companies}
            if position_to_company:
                self.graph_builder.add_issued_by_relationships(position_to_company)
                self.stats.graph_relationships_created += len(position_to_company)

            # Add HEADQUARTERED_IN relationships (company -> country)
            company_to_country = {}
            for ticker, company in companies.items():
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

        Args:
            portfolio: Portfolio to enrich
        """
        tickers = [p.ticker for p in portfolio.positions]
        if not tickers:
            return

        logger.info(f"Enriching prices for {len(tickers)} positions")
        try:
            response = self.factset_client.get_last_close_prices(tickers)
            
            # Map ticker -> (date, price)
            price_map = {}
            if "data" in response:
                for item in response["data"]:
                    ticker = item.get("requestId")
                    price = item.get("price")
                    date_str = item.get("date")
                    
                    if ticker and price is not None and date_str:
                        # If we already have a price for this ticker, check if this one is newer
                        if ticker in price_map:
                            existing_date, _ = price_map[ticker]
                            if date_str > existing_date:
                                price_map[ticker] = (date_str, float(price))
                        else:
                            price_map[ticker] = (date_str, float(price))
            
            # Update positions
            updated_count = 0
            for position in portfolio.positions:
                if position.ticker in price_map:
                    _, price = price_map[position.ticker]
                    position.market_value = position.quantity * price
                    updated_count += 1
            
            logger.info(f"Updated market values for {updated_count} positions")
            
            # Recalculate weights
            portfolio.calculate_weights()
            
        except Exception as e:
            logger.error(f"Failed to enrich prices: {e}")
            self.stats.add_error(f"Price enrichment failed: {e}")

    def execute(self, portfolio_file: str) -> Tuple[Optional[Portfolio], List[str], PipelineStatistics]:
        """Execute full ETL pipeline.

        Args:
            portfolio_file: Path to portfolio CSV file

        Returns:
            Tuple of (Portfolio, Cypher statements, statistics)
        """
        logger.info("=" * 70)
        logger.info("Starting ETL Pipeline")
        logger.info("=" * 70)

        # Step 1: Load portfolio
        portfolio = self.load_portfolio(portfolio_file)
        if not portfolio:
            logger.error("Pipeline failed: Could not load portfolio")
            return None, [], self.stats

        # Step 2: Enrich prices
        self.enrich_prices(portfolio)

        # Step 3: Enrich positions (company data)
        companies, countries, executives = self.enrich_positions(portfolio.positions)

        # Step 4: Build graph
        statements = self.build_graph(portfolio, companies, countries, executives)

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
