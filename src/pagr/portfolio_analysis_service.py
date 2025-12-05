"""Portfolio analysis service wrapping QueryService with multi-portfolio support.

This service provides a consistent interface for portfolio analysis queries,
handling multi-portfolio logic, error handling, and result formatting.
"""

import logging
from typing import List, Union, Optional, Dict, Any
from pagr.fds.graph.queries import QueryService, QueryResult

logger = logging.getLogger(__name__)


class PortfolioAnalysisService:
    """Wrapper around QueryService with multi-portfolio optimizations."""

    def __init__(self, query_service: QueryService):
        """Initialize analysis service.

        Args:
            query_service: QueryService instance for executing Cypher queries
        """
        self.query_service = query_service
        logger.info("Initialized PortfolioAnalysisService")

    def _normalize_portfolios(self, portfolio_names: Union[str, List[str]]) -> List[str]:
        """Normalize portfolio names to list format.

        Args:
            portfolio_names: Single name (str) or list of names

        Returns:
            List of portfolio names
        """
        if isinstance(portfolio_names, str):
            return [portfolio_names]
        return portfolio_names

    def sector_exposure(self, portfolio_names: Union[str, List[str]]) -> Optional[QueryResult]:
        """Get sector exposure for portfolio(s).

        Args:
            portfolio_names: Portfolio name(s)

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.sector_exposure(portfolio_names)
            logger.info(f"Sector exposure query returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Sector exposure query failed: {e}")
            return None

    def country_breakdown(self, portfolio_names: Union[str, List[str]]) -> Optional[QueryResult]:
        """Get country breakdown for portfolio(s).

        Args:
            portfolio_names: Portfolio name(s)

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.country_breakdown(portfolio_names)
            logger.info(f"Country breakdown query returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Country breakdown query failed: {e}")
            return None

    def country_exposure(
        self,
        portfolio_names: Union[str, List[str]],
        country_iso: str
    ) -> Optional[QueryResult]:
        """Get exposure to specific country for portfolio(s).

        Args:
            portfolio_names: Portfolio name(s)
            country_iso: ISO code of country

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.country_exposure(portfolio_names, country_iso)
            logger.info(f"Country exposure query for {country_iso} returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Country exposure query failed: {e}")
            return None

    def sector_positions(
        self,
        portfolio_names: Union[str, List[str]],
        sector: str
    ) -> Optional[QueryResult]:
        """Get all positions in specific sector for portfolio(s).

        Args:
            portfolio_names: Portfolio name(s)
            sector: Sector name

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.sector_positions(portfolio_names, sector)
            logger.info(f"Sector positions query for {sector} returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Sector positions query failed: {e}")
            return None

    def country_positions(
        self,
        portfolio_names: Union[str, List[str]],
        country_iso: str
    ) -> Optional[QueryResult]:
        """Get all positions in specific country for portfolio(s).

        Args:
            portfolio_names: Portfolio name(s)
            country_iso: ISO code of country

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.country_positions(portfolio_names, country_iso)
            logger.info(f"Country positions query for {country_iso} returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Country positions query failed: {e}")
            return None

    def executive_lookup(self, portfolio_names: Union[str, List[str]]) -> Optional[QueryResult]:
        """Get executives of portfolio companies.

        Args:
            portfolio_names: Portfolio name(s)

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.executive_lookup(portfolio_names)
            logger.info(f"Executive lookup returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Executive lookup failed: {e}")
            return None

    def company_exposure(
        self,
        portfolio_names: Union[str, List[str]],
        company_name: str
    ) -> Optional[QueryResult]:
        """Get exposure to specific company.

        Args:
            portfolio_names: Portfolio name(s)
            company_name: Name of company

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.company_exposure(portfolio_names, company_name)
            logger.info(f"Company exposure query for {company_name} returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Company exposure query failed: {e}")
            return None

    def total_company_exposure(
        self,
        portfolio_names: Union[str, List[str]],
        company_ticker: str
    ) -> Optional[QueryResult]:
        """Get total exposure to company including subsidiaries.

        Args:
            portfolio_names: Portfolio name(s)
            company_ticker: Ticker of company

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.total_company_exposure(portfolio_names, company_ticker)
            logger.info(f"Total company exposure query for {company_ticker} returned {result.record_count} records")
            return result
        except Exception as e:
            logger.error(f"Total company exposure query failed: {e}")
            return None

    def sector_region_stress(
        self,
        portfolio_names: Union[str, List[str]],
        sector: str,
        region: str
    ) -> Optional[QueryResult]:
        """What-if analysis for sector slowdown in region.

        Args:
            portfolio_names: Portfolio name(s)
            sector: Sector name
            region: Region name

        Returns:
            QueryResult or None if query fails
        """
        try:
            result = self.query_service.sector_region_stress(portfolio_names, sector, region)
            logger.info(
                f"Sector-region stress query for {sector}/{region} returned {result.record_count} records"
            )
            return result
        except Exception as e:
            logger.error(f"Sector-region stress query failed: {e}")
            return None

    def aggregate_sectors(self, sector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate sector exposure across multiple portfolio queries.

        Already handled by database queries using SUM(), but provided for
        completeness if client-side aggregation is needed.

        Args:
            sector_results: List of sector exposure records

        Returns:
            Aggregated sector data
        """
        if not sector_results:
            return []

        # Since database queries already aggregate, just return as-is
        logger.debug(f"Sector results already aggregated by database ({len(sector_results)} sectors)")
        return sector_results
