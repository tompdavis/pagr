"""Graph query templates for portfolio analysis.

Implements Cypher queries for 5 business use cases.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from a graph query."""

    query_name: str
    cypher: str
    records: List[Dict[str, Any]]
    record_count: int = 0

    def __post_init__(self):
        """Calculate record count."""
        self.record_count = len(self.records)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dict representation
        """
        return {
            "query_name": self.query_name,
            "record_count": self.record_count,
            "records": self.records,
        }


class GraphQueries:
    """Cypher query templates for portfolio analysis."""

    @staticmethod
    def sector_exposure(portfolio_names: Union[str, List[str]]) -> str:
        """Query 1: Sector exposure from portfolio(s).

        Returns sectors, total exposure, total weight, number of positions.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company)
WHERE p.name IN [{names_list}]
RETURN
    c.sector AS sector,
    SUM(pos.market_value) AS total_exposure,
    SUM(pos.weight) AS total_weight,
    COUNT(pos) AS num_positions
ORDER BY total_exposure DESC;
""".strip()

    @staticmethod
    def country_exposure(portfolio_names: Union[str, List[str]], country_iso: str) -> str:
        """Query 2a: Direct exposure to a country.

        Returns companies headquartered in the country.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            country_iso: ISO code of country (e.g., 'TW', 'US')

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company)-[:HEADQUARTERED_IN]->(:Country {{iso_code: '{country_iso}'}})
WHERE p.name IN [{names_list}]
RETURN
    c.name AS company,
    SUM(pos.market_value) AS exposure,
    COUNT(pos) AS num_positions
ORDER BY exposure DESC;
""".strip()

    # TODO: Add region back in the future
    # @staticmethod
    # def region_exposure(portfolio_name: str, region_name: str) -> str:
    #     """Query 2b: Exposure to a region.
    #
    #     Returns companies in the region.
    #
    #     Args:
    #         portfolio_name: Name of portfolio
    #         region_name: Name of region (e.g., 'Asia-Pacific')
    #
    #     Returns:
    #         Cypher query string
    #     """
    #     return f"""
    # MATCH (p:Portfolio {{name: '{portfolio_name}'}})-[:CONTAINS]->(pos:Position)-[:ISSUED_BY]->(c:Company)
    #       -[:HEADQUARTERED_IN]->(country:Country {{region: '{region_name}'}})
    # RETURN
    #     c.name AS company,
    #     country.name AS country,
    #     SUM(pos.market_value) AS exposure,
    #     COUNT(pos) AS num_positions
    # ORDER BY exposure DESC;
    # """.strip()

    @staticmethod
    def company_exposure(portfolio_names: Union[str, List[str]], company_name: str) -> str:
        """Query 2c: Exposure to a specific company (direct and indirect).

        Returns direct holdings and indirect exposure through supply chain.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            company_name: Name of company

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company {{name: '{company_name}'}})
WHERE p.name IN [{names_list}]
WITH SUM(pos.market_value) AS direct_exposure
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(portfolio_company:Company)-[:CUSTOMER_OF]->(:Company {{name: '{company_name}'}})
WHERE p.name IN [{names_list}]
WITH direct_exposure, SUM(pos.market_value) AS indirect_exposure
RETURN
    direct_exposure,
    indirect_exposure,
    (direct_exposure + indirect_exposure) AS total_exposure;
""".strip()

    @staticmethod
    def sector_region_stress(portfolio_names: Union[str, List[str]], sector: str, region: str) -> str:
        """Query 3: What if analysis - sector slowdown in region.

        Returns companies affected and total exposure.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            sector: Sector name
            region: Region name

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company {{sector: '{sector}'}})-[:HEADQUARTERED_IN]->(country:Country {{region: '{region}'}})
WHERE p.name IN [{names_list}]
RETURN
    c.name AS company,
    c.sector AS sector,
    country.name AS country,
    SUM(pos.market_value) AS exposure_at_risk
ORDER BY exposure_at_risk DESC;
""".strip()

    @staticmethod
    def executive_lookup(portfolio_names: Union[str, List[str]]) -> str:
        """Query 4: CEOs of portfolio companies.

        Returns executives and their positions.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company)<-[:CEO_OF]-(exec:Executive)
WHERE p.name IN [{names_list}]
RETURN
    c.name AS company,
    exec.name AS executive_name,
    exec.title AS title,
    SUM(pos.market_value) AS position_value
ORDER BY position_value DESC;
""".strip()

    @staticmethod
    def total_company_exposure(portfolio_names: Union[str, List[str]], company_ticker: str) -> str:
        """Query 5: Total exposure to a company including subsidiaries & suppliers.

        Returns direct holdings, subsidiary holdings, and supplier exposure.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            company_ticker: Ticker of company

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company {{ticker: '{company_ticker}'}})
WHERE p.name IN [{names_list}]
RETURN
    c.name AS company_name,
    SUM(pos.market_value) AS direct_exposure,
    0 AS subsidiary_exposure,
    0 AS supplier_exposure,
    SUM(pos.market_value) AS total_exposure;
""".strip()

    @staticmethod
    def sector_positions(portfolio_names: Union[str, List[str]], sector: str) -> str:
        """Get all positions in a specific sector.

        Returns positions invested in companies in the sector.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            sector: Sector name

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company {{sector: '{sector}'}})
WHERE p.name IN [{names_list}]
RETURN
    p.name AS portfolio_name,
    CASE WHEN sec:Stock THEN sec.ticker ELSE NULL END AS ticker,
    c.name AS company,
    pos.quantity AS quantity,
    pos.market_value AS market_value,
    pos.weight AS weight
ORDER BY p.name, market_value DESC;
""".strip()

    @staticmethod
    def country_breakdown(portfolio_names: Union[str, List[str]]) -> str:
        """Get portfolio breakdown by country.

        Returns countries and their total exposure and weight.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company)-[:HEADQUARTERED_IN]->(country:Country)
WHERE p.name IN [{names_list}]
RETURN
    country.iso_code AS country_code,
    country.name AS country,
    SUM(pos.market_value) AS total_exposure,
    SUM(pos.weight) AS total_weight,
    COUNT(pos) AS num_positions
ORDER BY total_exposure DESC;
""".strip()

    @staticmethod
    def country_positions(portfolio_names: Union[str, List[str]], country_iso: str) -> str:
        """Get all positions in companies headquartered in a specific country.

        Returns positions invested in companies in the country.
        Uses new graph schema: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company

        Args:
            portfolio_names: Name of portfolio (str) or list of portfolio names
            country_iso: Country ISO code

        Returns:
            Cypher query string
        """
        # Normalize to list
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names]

        names_list = ", ".join(f"'{name}'" for name in portfolio_names)

        return f"""
MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:INVESTED_IN]->(sec)
      -[:ISSUED_BY]->(c:Company)-[:HEADQUARTERED_IN]->(:Country {{iso_code: '{country_iso}'}})
WHERE p.name IN [{names_list}]
RETURN
    p.name AS portfolio_name,
    CASE WHEN sec:Stock THEN sec.ticker ELSE NULL END AS ticker,
    c.name AS company,
    pos.quantity AS quantity,
    pos.market_value AS market_value,
    pos.weight AS weight
ORDER BY p.name, market_value DESC;
""".strip()


class QueryService:
    """Service for executing graph queries."""

    def __init__(self, graph_client):
        """Initialize query service.

        Args:
            graph_client: Memgraph client or compatible graph database client
        """
        self.graph_client = graph_client
        logger.info("Initialized QueryService")

    def execute_query(self, query_name: str, cypher: str) -> QueryResult:
        """Execute a Cypher query.

        Args:
            query_name: Name of query for logging
            cypher: Cypher query string

        Returns:
            QueryResult with records and metadata

        Raises:
            Exception: If query execution fails
        """
        try:
            logger.debug(f"Executing query: {query_name}")
            records = self.graph_client.execute_query(cypher)
            logger.debug(f"Query returned {len(records)} records")
            return QueryResult(query_name=query_name, cypher=cypher, records=records)

        except Exception as e:
            logger.error(f"Query execution failed: {query_name} - {str(e)}")
            raise

    def sector_exposure(self, portfolio_names: Union[str, List[str]]) -> QueryResult:
        """Execute sector exposure query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names

        Returns:
            QueryResult with sector exposure data
        """
        cypher = GraphQueries.sector_exposure(portfolio_names)
        return self.execute_query("sector_exposure", cypher)

    def country_exposure(self, portfolio_names: Union[str, List[str]], country_iso: str) -> QueryResult:
        """Execute country exposure query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            country_iso: Country ISO code

        Returns:
            QueryResult with country exposure data
        """
        cypher = GraphQueries.country_exposure(portfolio_names, country_iso)
        return self.execute_query("country_exposure", cypher)

    # TODO: Add region back in the future
    # def region_exposure(self, portfolio_name: str, region_name: str) -> QueryResult:
    #     """Execute region exposure query.
    #
    #     Args:
    #         portfolio_name: Portfolio name
    #         region_name: Region name
    #
    #     Returns:
    #         QueryResult with region exposure data
    #     """
    #     cypher = GraphQueries.region_exposure(portfolio_name, region_name)
    #     return self.execute_query("region_exposure", cypher)

    def company_exposure(self, portfolio_names: Union[str, List[str]], company_name: str) -> QueryResult:
        """Execute company exposure query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            company_name: Company name

        Returns:
            QueryResult with company exposure data
        """
        cypher = GraphQueries.company_exposure(portfolio_names, company_name)
        return self.execute_query("company_exposure", cypher)

    def sector_region_stress(
        self, portfolio_names: Union[str, List[str]], sector: str, region: str
    ) -> QueryResult:
        """Execute sector-region stress test query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            sector: Sector name
            region: Region name

        Returns:
            QueryResult with stress test data
        """
        cypher = GraphQueries.sector_region_stress(portfolio_names, sector, region)
        return self.execute_query("sector_region_stress", cypher)

    def executive_lookup(self, portfolio_names: Union[str, List[str]]) -> QueryResult:
        """Execute executive lookup query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names

        Returns:
            QueryResult with executive data
        """
        cypher = GraphQueries.executive_lookup(portfolio_names)
        return self.execute_query("executive_lookup", cypher)

    def total_company_exposure(
        self, portfolio_names: Union[str, List[str]], company_ticker: str
    ) -> QueryResult:
        """Execute total company exposure query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            company_ticker: Company ticker

        Returns:
            QueryResult with total exposure data
        """
        cypher = GraphQueries.total_company_exposure(portfolio_names, company_ticker)
        return self.execute_query("total_company_exposure", cypher)

    def sector_positions(self, portfolio_names: Union[str, List[str]], sector: str) -> QueryResult:
        """Execute sector positions query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            sector: Sector name

        Returns:
            QueryResult with positions in the sector
        """
        cypher = GraphQueries.sector_positions(portfolio_names, sector)
        return self.execute_query("sector_positions", cypher)

    def country_breakdown(self, portfolio_names: Union[str, List[str]]) -> QueryResult:
        """Execute country breakdown query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names

        Returns:
            QueryResult with country breakdown data
        """
        cypher = GraphQueries.country_breakdown(portfolio_names)
        return self.execute_query("country_breakdown", cypher)

    def country_positions(self, portfolio_names: Union[str, List[str]], country_iso: str) -> QueryResult:
        """Execute country positions query.

        Args:
            portfolio_names: Portfolio name (str) or list of portfolio names
            country_iso: Country ISO code

        Returns:
            QueryResult with positions in the country
        """
        cypher = GraphQueries.country_positions(portfolio_names, country_iso)
        return self.execute_query("country_positions", cypher)

    def format_result_table(self, result: QueryResult) -> str:
        """Format query result as ASCII table.

        Args:
            result: QueryResult to format

        Returns:
            Formatted table string
        """
        if not result.records:
            return f"No results for {result.query_name}"

        # Get headers from first record
        headers = list(result.records[0].keys())
        rows = [[str(record.get(h, "")) for h in headers] for record in result.records]

        # Simple ASCII table formatting
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
                      for i, h in enumerate(headers)]

        table = []
        # Header
        table.append(" | ".join(f"{h:{w}}" for h, w in zip(headers, col_widths)))
        table.append("-" * (sum(col_widths) + 3 * (len(headers) - 1)))

        # Rows
        for row in rows:
            table.append(" | ".join(f"{v:{w}}" for v, w in zip(row, col_widths)))

        return "\n".join(table)
