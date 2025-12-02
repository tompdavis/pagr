"""Graph builder for constructing Cypher queries from FIBO entities.

Transforms enriched portfolio and company data into graph nodes and relationships.
Uses MERGE for entities (avoid duplicates) and CREATE for positions (unique per import).
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from pagr.fds.models.portfolio import Portfolio, Position
from pagr.fds.models.fibo import (
    Company,
    Country,
    Region,
    Executive,
    Stock,
    Bond,
    Derivative,
    Relationship,
    RelationshipType,
)
from pagr.fds.graph.schema import NodeLabel, RelationshipType as SchemaRelType

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds Cypher queries for graph database operations.

    Converts FIBO entities into Cypher CREATE/MERGE statements.
    Handles batching and performance optimization.
    """

    def __init__(self):
        """Initialize graph builder."""
        self.node_statements: List[str] = []
        self.relationship_statements: List[str] = []
        self.merge_set_statements: Dict[str, List[str]] = {}
        logger.debug("Initialized GraphBuilder")

    def clear(self) -> None:
        """Clear all accumulated statements."""
        self.node_statements = []
        self.relationship_statements = []
        self.merge_set_statements = {}

    def add_portfolio_nodes(self, portfolio: Portfolio) -> None:
        """Add portfolio node to graph.

        Args:
            portfolio: Portfolio instance
        """
        name = self._escape_string(portfolio.name)
        created_at = portfolio.created_at or datetime.now().isoformat()
        total_value = portfolio.total_value or 0.0

        query = (
            f"MERGE (p:Portfolio {{"
            f"name: '{name}', "
            f"created_at: '{created_at}', "
            f"total_value: {total_value}"
            f"}}) "
            f"RETURN p;"
        )
        self.node_statements.append(query)
        logger.debug(f"Added portfolio node: {portfolio.name}")

    def add_position_nodes(self, positions: List[Position], portfolio_name: str) -> None:
        """Add position nodes and CONTAINS relationships.

        Positions are unique per portfolio import, so use CREATE not MERGE.

        Args:
            positions: List of Position instances
            portfolio_name: Name of parent portfolio
        """
        portfolio_name_escaped = self._escape_string(portfolio_name)

        for pos in positions:
            ticker = self._escape_string(pos.ticker)
            ticker_var = ticker.replace("-", "_").replace(".", "_")  # Sanitize for use as Cypher variable
            quantity = pos.quantity
            market_value = pos.market_value
            security_type = self._escape_string(pos.security_type or "Unknown")
            weight = pos.weight or 0.0

            # Create position node
            isin = f", isin: '{self._escape_string(pos.isin)}'" if pos.isin else ""
            cusip = f", cusip: '{self._escape_string(pos.cusip)}'" if pos.cusip else ""
            cost_basis = f", cost_basis: {pos.cost_basis}" if pos.cost_basis else ""
            purchase_date = (
                f", purchase_date: '{self._escape_string(pos.purchase_date)}'"
                if pos.purchase_date
                else ""
            )

            position_query = (
                f"CREATE (pos_{ticker_var}:Position {{"
                f"ticker: '{ticker}', "
                f"quantity: {quantity}, "
                f"market_value: {market_value}, "
                f"security_type: '{security_type}', "
                f"weight: {weight}"
                f"{isin}{cusip}{cost_basis}{purchase_date}"
                f"}}) "
                f"RETURN pos_{ticker_var};"
            )
            self.node_statements.append(position_query)

            # Create CONTAINS relationship
            contains_query = (
                f"MATCH (p:Portfolio {{name: '{portfolio_name_escaped}'}}), "
                f"(pos:Position {{ticker: '{ticker}'}}) "
                f"CREATE (p)-[:CONTAINS {{weight: {weight}}}]->(pos);"
            )
            self.relationship_statements.append(contains_query)

        logger.debug(f"Added {len(positions)} position nodes")

    def add_company_nodes(self, companies: Dict[str, Company]) -> None:
        """Add company nodes.

        Uses MERGE to avoid duplicates.

        Args:
            companies: Dict of ticker -> Company
        """
        for ticker, company in companies.items():
            fibo_id = self._escape_string(company.fibo_id)
            factset_id = self._escape_string(company.factset_id) if company.factset_id else ""
            name = self._escape_string(company.name)
            ticker_clean = self._escape_string(ticker)
            sector = self._escape_string(company.sector) if company.sector else ""
            industry = self._escape_string(company.industry) if company.industry else ""
            country = self._escape_string(company.country) if company.country else ""

            market_cap = company.market_cap or 0.0
            description = self._escape_string(company.description) if company.description else ""

            factset_clause = f", c.factset_id = '{factset_id}'" if factset_id else ""
            sector_clause = f", c.sector = '{sector}'" if sector else ""
            industry_clause = f", c.industry = '{industry}'" if industry else ""
            country_clause = f", c.country = '{country}'" if country else ""
            market_cap_clause = f", c.market_cap = {market_cap}"
            description_clause = f", c.description = '{description}'" if description else ""

            query = (
                f"MERGE (c:Company {{fibo_id: '{fibo_id}'}}) "
                f"SET c.name = '{name}', "
                f"c.ticker = '{ticker_clean}' "
                f"{factset_clause}"
                f"{market_cap_clause} "
                f"{sector_clause}"
                f"{industry_clause}"
                f"{country_clause}"
                f"{description_clause} "
                f"RETURN c;"
            )
            self.node_statements.append(query)

        logger.debug(f"Added {len(companies)} company nodes")

    def add_country_nodes(self, countries: Dict[str, Country]) -> None:
        """Add country nodes.

        Uses MERGE to avoid duplicates.

        Args:
            countries: Dict of iso_code -> Country
        """
        for iso_code, country in countries.items():
            fibo_id = self._escape_string(country.fibo_id)
            name = self._escape_string(country.name)
            iso_clean = self._escape_string(iso_code)
            region = self._escape_string(country.region) if country.region else ""

            region_clause = f", region: '{region}'" if region else ""

            query = (
                f"MERGE (c:Country {{fibo_id: '{fibo_id}'}}) "
                f"SET c.name = '{name}', "
                f"c.iso_code = '{iso_clean}' "
                f"{region_clause} "
                f"RETURN c;"
            )
            self.node_statements.append(query)

        logger.debug(f"Added {len(countries)} country nodes")

    def add_executive_nodes(self, executives: Dict[str, Executive]) -> None:
        """Add executive nodes.

        Uses MERGE with fibo_id as unique identifier.

        Args:
            executives: Dict of fibo_id -> Executive
        """
        for fibo_id, executive in executives.items():
            fibo_id_clean = self._escape_string(fibo_id)
            name = self._escape_string(executive.name)
            title = self._escape_string(executive.title) if executive.title else ""
            start_date = self._escape_string(executive.start_date) if executive.start_date else ""

            title_clause = f", title: '{title}'" if title else ""
            start_date_clause = f", start_date: '{start_date}'" if start_date else ""

            query = (
                f"MERGE (e:Executive {{fibo_id: '{fibo_id_clean}'}}) "
                f"SET e.name = '{name}' "
                f"{title_clause}"
                f"{start_date_clause} "
                f"RETURN e;"
            )
            self.node_statements.append(query)

        logger.debug(f"Added {len(executives)} executive nodes")

    def add_security_nodes(
        self, stocks: Dict[str, Stock] = None, bonds: Dict[str, Bond] = None
    ) -> None:
        """Add stock and bond nodes.

        Args:
            stocks: Dict of ticker -> Stock
            bonds: Dict of ticker -> Bond
        """
        stocks = stocks or {}
        bonds = bonds or {}

        for ticker, stock in stocks.items():
            fibo_id = self._escape_string(stock.fibo_id)
            ticker_clean = self._escape_string(ticker)
            security_type = self._escape_string(stock.security_type) if stock.security_type else "Stock"
            isin = self._escape_string(stock.isin) if stock.isin else ""
            cusip = self._escape_string(stock.cusip) if stock.cusip else ""
            sedol = self._escape_string(stock.sedol) if stock.sedol else ""

            isin_clause = f", isin: '{isin}'" if isin else ""
            cusip_clause = f", cusip: '{cusip}'" if cusip else ""
            sedol_clause = f", sedol: '{sedol}'" if sedol else ""

            query = (
                f"MERGE (s:Stock {{fibo_id: '{fibo_id}'}}) "
                f"SET s.ticker = '{ticker_clean}', "
                f"s.security_type = '{security_type}' "
                f"{isin_clause}"
                f"{cusip_clause}"
                f"{sedol_clause} "
                f"RETURN s;"
            )
            self.node_statements.append(query)

        for ticker, bond in bonds.items():
            fibo_id = self._escape_string(bond.fibo_id)
            ticker_clean = self._escape_string(ticker)
            isin = self._escape_string(bond.isin) if bond.isin else ""
            cusip = self._escape_string(bond.cusip) if bond.cusip else ""
            security_type = self._escape_string(bond.security_type) if bond.security_type else "Bond"

            isin_clause = f", isin: '{isin}'" if isin else ""
            cusip_clause = f", cusip: '{cusip}'" if cusip else ""

            query = (
                f"MERGE (b:Bond {{fibo_id: '{fibo_id}'}}) "
                f"SET b.ticker = '{ticker_clean}', "
                f"b.security_type = '{security_type}' "
                f"{isin_clause}"
                f"{cusip_clause} "
                f"RETURN b;"
            )
            self.node_statements.append(query)

        logger.debug(f"Added {len(stocks)} stock nodes and {len(bonds)} bond nodes")

    def add_issued_by_relationships(self, position_to_company: Dict[str, str]) -> None:
        """Add ISSUED_BY relationships between positions and companies.

        Args:
            position_to_company: Dict of position_ticker -> company_fibo_id
        """
        for pos_ticker, company_fibo_id in position_to_company.items():
            pos_ticker_clean = self._escape_string(pos_ticker)
            company_fibo_id_clean = self._escape_string(company_fibo_id)

            query = (
                f"MATCH (pos:Position {{ticker: '{pos_ticker_clean}'}}), "
                f"(c:Company {{fibo_id: '{company_fibo_id_clean}'}}) "
                f"CREATE (pos)-[:ISSUED_BY]->(c);"
            )
            self.relationship_statements.append(query)

        logger.debug(f"Added {len(position_to_company)} ISSUED_BY relationships")

    def add_holds_relationships(self, position_to_security: Dict[str, Tuple[str, str]]) -> None:
        """Add HOLDS relationships between positions and securities.

        Args:
            position_to_security: Dict of position_ticker -> (security_type, security_fibo_id)
                                security_type is 'stock' or 'bond'
        """
        for pos_ticker, (sec_type, sec_fibo_id) in position_to_security.items():
            pos_ticker_clean = self._escape_string(pos_ticker)
            sec_fibo_id_clean = self._escape_string(sec_fibo_id)
            label = "Stock" if sec_type.lower() == "stock" else "Bond"

            query = (
                f"MATCH (pos:Position {{ticker: '{pos_ticker_clean}'}}), "
                f"(s:{label} {{fibo_id: '{sec_fibo_id_clean}'}}) "
                f"CREATE (pos)-[:HOLDS]->(s);"
            )
            self.relationship_statements.append(query)

        logger.debug(f"Added {len(position_to_security)} HOLDS relationships")

    def add_company_relationships(self, relationships: List[Relationship]) -> None:
        """Add relationships between companies and other entities.

        Args:
            relationships: List of Relationship instances
        """
        for rel in relationships:
            source_fibo_id = self._escape_string(rel.source_fibo_id)
            target_fibo_id = self._escape_string(rel.target_fibo_id)
            rel_type = rel.rel_type

            # Map relationship type to schema type
            schema_rel_type = self._map_relationship_type(rel_type)

            # Build property clause if properties exist
            properties = ""
            if rel.properties:
                props = []
                for key, value in rel.properties.items():
                    if isinstance(value, str):
                        props.append(f"{key}: '{self._escape_string(value)}'")
                    elif isinstance(value, (int, float)):
                        props.append(f"{key}: {value}")
                if props:
                    properties = f" {{{', '.join(props)}}}"

            # Determine source and target node types
            source_label = self._get_entity_label(rel.source_type)
            target_label = self._get_entity_label(rel.target_type)

            query = (
                f"MATCH (s:{source_label} {{fibo_id: '{source_fibo_id}'}}), "
                f"(t:{target_label} {{fibo_id: '{target_fibo_id}'}}) "
                f"CREATE (s)-[:{schema_rel_type}{properties}]->(t);"
            )
            self.relationship_statements.append(query)

        logger.debug(f"Added {len(relationships)} company relationships")

    def add_headquartered_in_relationships(
        self, company_to_country: Dict[str, str]
    ) -> None:
        """Add HEADQUARTERED_IN relationships between companies and countries.

        Args:
            company_to_country: Dict of company_fibo_id -> country_iso_code
        """
        for company_fibo_id, country_iso in company_to_country.items():
            company_fibo_id_clean = self._escape_string(company_fibo_id)
            country_iso_clean = self._escape_string(country_iso)

            # MERGE country to create it if it doesn't exist
            query = (
                f"MATCH (c:Company {{fibo_id: '{company_fibo_id_clean}'}}) "
                f"MERGE (co:Country {{iso_code: '{country_iso_clean}'}}) "
                f"CREATE (c)-[:HEADQUARTERED_IN]->(co);"
            )
            self.relationship_statements.append(query)

        logger.debug(f"Added {len(company_to_country)} HEADQUARTERED_IN relationships")

    def add_ceo_of_relationships(self, executive_to_company: Dict[str, str]) -> None:
        """Add CEO_OF relationships between executives and companies.

        Args:
            executive_to_company: Dict of executive_fibo_id -> company_fibo_id
        """
        for exec_fibo_id, company_fibo_id in executive_to_company.items():
            exec_fibo_id_clean = self._escape_string(exec_fibo_id)
            company_fibo_id_clean = self._escape_string(company_fibo_id)

            query = (
                f"MATCH (e:Executive {{fibo_id: '{exec_fibo_id_clean}'}}), "
                f"(c:Company {{fibo_id: '{company_fibo_id_clean}'}}) "
                f"CREATE (e)-[:CEO_OF]->(c);"
            )
            self.relationship_statements.append(query)

        logger.debug(f"Added {len(executive_to_company)} CEO_OF relationships")

    def get_node_statements(self) -> List[str]:
        """Get all accumulated node creation statements.

        Returns:
            List of Cypher node creation statements
        """
        return self.node_statements

    def get_relationship_statements(self) -> List[str]:
        """Get all accumulated relationship creation statements.

        Returns:
            List of Cypher relationship creation statements
        """
        return self.relationship_statements

    def get_all_statements(self) -> List[str]:
        """Get all accumulated statements (nodes then relationships).

        Returns:
            List of all Cypher statements
        """
        return self.node_statements + self.relationship_statements

    def get_batch_statements(self) -> Dict[str, List[str]]:
        """Get statements organized by batch type.

        Returns:
            Dict with 'nodes' and 'relationships' keys
        """
        return {
            "nodes": self.node_statements,
            "relationships": self.relationship_statements,
        }

    @staticmethod
    def _escape_string(value: str) -> str:
        """Escape string for Cypher queries.

        Handles single quotes by doubling them.

        Args:
            value: String to escape

        Returns:
            Escaped string safe for Cypher
        """
        if not isinstance(value, str):
            return str(value)
        return value.replace("'", "''")

    @staticmethod
    def _map_relationship_type(rel_type: str) -> str:
        """Map relationship type to Cypher relationship type.

        Args:
            rel_type: Relationship type string

        Returns:
            Cypher relationship type (uppercase)
        """
        type_map = {
            RelationshipType.HAS_SUBSIDIARY: SchemaRelType.HAS_SUBSIDIARY,
            RelationshipType.SUBSIDIARY_OF: SchemaRelType.SUBSIDIARY_OF,
            RelationshipType.OPERATES_IN: SchemaRelType.OPERATES_IN,
            RelationshipType.SUPPLIES_TO: SchemaRelType.SUPPLIES_TO,
            RelationshipType.CUSTOMER_OF: SchemaRelType.CUSTOMER_OF,
            RelationshipType.PARENT_OF: SchemaRelType.PARENT_OF,
        }
        return type_map.get(rel_type, rel_type.upper())

    @staticmethod
    def _get_entity_label(entity_type: str) -> str:
        """Get node label for entity type.

        Args:
            entity_type: Entity type string

        Returns:
            Node label for Cypher query
        """
        type_map = {
            "company": NodeLabel.COMPANY,
            "country": NodeLabel.COUNTRY,
            "region": NodeLabel.REGION,
            "executive": NodeLabel.EXECUTIVE,
            "stock": NodeLabel.STOCK,
            "bond": NodeLabel.BOND,
            "derivative": NodeLabel.DERIVATIVE,
        }
        return type_map.get(entity_type.lower(), "Entity")
