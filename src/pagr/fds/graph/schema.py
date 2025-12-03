"""FIBO graph database schema definitions for Memgraph."""

import logging

logger = logging.getLogger(__name__)


class NodeLabel:
    """Node labels for FIBO ontology in graph database."""

    PORTFOLIO = "Portfolio"
    POSITION = "Position"
    COMPANY = "Company"
    COUNTRY = "Country"
    REGION = "Region"
    EXECUTIVE = "Executive"
    STOCK = "Stock"
    BOND = "Bond"
    DERIVATIVE = "Derivative"


class RelationshipType:
    """Relationship types for FIBO ontology in graph database."""

    # Portfolio relationships
    CONTAINS = "CONTAINS"  # Portfolio -> Position

    # Position relationships (new hierarchy: Position -> INVESTED_IN -> Security -> ISSUED_BY -> Company)
    INVESTED_IN = "INVESTED_IN"  # Position -> Stock/Bond/Derivative
    HOLDS = "HOLDS"  # Position -> Stock/Bond/Derivative (deprecated, use INVESTED_IN)

    # Company relationships
    HAS_SUBSIDIARY = "HAS_SUBSIDIARY"  # Company -> Company
    SUBSIDIARY_OF = "SUBSIDIARY_OF"  # Company -> Company
    PARENT_OF = "PARENT_OF"  # Company -> Company

    # Geographic relationships
    HEADQUARTERED_IN = "HEADQUARTERED_IN"  # Company -> Country
    OPERATES_IN = "OPERATES_IN"  # Company -> Country

    # Supply chain relationships
    SUPPLIES_TO = "SUPPLIES_TO"  # Company -> Company
    CUSTOMER_OF = "CUSTOMER_OF"  # Company -> Company

    # Leadership relationships
    CEO_OF = "CEO_OF"  # Executive -> Company
    LEADS = "LEADS"  # Executive -> Company

    # Security relationships
    ISSUED_BY = "ISSUED_BY"  # Stock/Bond -> Company

    # Geographic structure
    PART_OF = "PART_OF"  # Country -> Region


class IndexDefinition:
    """Index definitions for performance optimization."""

    @staticmethod
    def get_indexes():
        """Get list of index creation statements.

        Returns:
            List of Cypher index creation statements
        """
        return [
            # Company indexes
            "CREATE INDEX ON :Company(factset_id);",
            "CREATE INDEX ON :Company(ticker);",
            "CREATE INDEX ON :Company(name);",
            "CREATE INDEX ON :Company(sector);",
            "CREATE INDEX ON :Company(country);",
            # Country indexes
            "CREATE INDEX ON :Country(iso_code);",
            "CREATE INDEX ON :Country(name);",
            # Position indexes
            "CREATE INDEX ON :Position(ticker);",
            # Executive indexes
            "CREATE INDEX ON :Executive(name);",
            # Stock/Bond indexes
            "CREATE INDEX ON :Stock(isin);",
            "CREATE INDEX ON :Stock(ticker);",
            "CREATE INDEX ON :Bond(isin);",
        ]


class ConstraintDefinition:
    """Constraint definitions for data integrity."""

    @staticmethod
    def get_constraints():
        """Get list of constraint creation statements.

        Returns:
            List of Cypher constraint creation statements
        """
        return [
            # Unique constraints (if supported by Memgraph)
            # Note: Memgraph may not support all Neo4j constraint types
            # Fallback to indexes if needed
        ]


class NodeProperties:
    """Property definitions for each node type."""

    @staticmethod
    def portfolio():
        """Portfolio node properties."""
        return {
            "name": "string",  # Portfolio name
            "created_at": "string",  # ISO timestamp
            "total_value": "float",  # Total portfolio value
        }

    @staticmethod
    def position():
        """Position node properties."""
        return {
            "ticker": "string",  # Security ticker
            "quantity": "float",  # Number of shares
            "market_value": "float",  # Market value in USD
            "security_type": "string",  # Stock, Bond, Derivative, etc.
            "weight": "float",  # Portfolio weight (%)
            "isin": "string",  # Optional ISIN
            "cusip": "string",  # Optional CUSIP
            "cost_basis": "float",  # Optional cost basis
            "purchase_date": "string",  # Optional purchase date (ISO)
        }

    @staticmethod
    def company():
        """Company node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "factset_id": "string",  # FactSet entity ID
            "name": "string",  # Company name
            "ticker": "string",  # Primary ticker
            "sector": "string",  # GICS sector
            "industry": "string",  # GICS industry
            "market_cap": "float",  # Market capitalization (USD)
            "description": "string",  # Business description
            "country": "string",  # Headquarters country
            "created_at": "string",  # ISO timestamp
            "updated_at": "string",  # ISO timestamp
        }

    @staticmethod
    def country():
        """Country node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "name": "string",  # Country name
            "iso_code": "string",  # ISO 3166-1 alpha-2 code
            "region": "string",  # Geographic region
        }

    @staticmethod
    def region():
        """Region node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "name": "string",  # Region name
            "description": "string",  # Region description
        }

    @staticmethod
    def executive():
        """Executive node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "name": "string",  # Full name
            "title": "string",  # Job title
            "start_date": "string",  # Start date (ISO format)
        }

    @staticmethod
    def stock():
        """Stock node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "ticker": "string",  # Stock ticker
            "security_type": "string",  # Security type
            "isin": "string",  # ISIN identifier
            "cusip": "string",  # CUSIP identifier
            "sedol": "string",  # SEDOL identifier
            "market_price": "float",  # Last close market price in USD
        }

    @staticmethod
    def bond():
        """Bond node properties."""
        return {
            "fibo_id": "string",  # Unique FIBO identifier
            "isin": "string",  # ISIN identifier (preferred)
            "cusip": "string",  # CUSIP identifier
            "security_type": "string",  # Bond type
            "coupon": "float",  # Annual coupon rate (%) - N/A if not available
            "currency": "string",  # Bond currency
            "market_price": "float",  # Clean price (excludes accrued interest) in USD
            "maturity_date": "string",  # Maturity date (ISO format)
        }


class RelationshipProperties:
    """Property definitions for relationships."""

    @staticmethod
    def has_subsidiary():
        """HAS_SUBSIDIARY relationship properties."""
        return {
            "ownership_percentage": "float",  # Ownership %
            "acquisition_date": "string",  # Acquisition date (ISO)
        }

    @staticmethod
    def operates_in():
        """OPERATES_IN relationship properties."""
        return {
            "revenue_percentage": "float",  # % of revenue from region
        }

    @staticmethod
    def supplies_to():
        """SUPPLIES_TO relationship properties."""
        return {
            "revenue_percentage": "float",  # % of supplier revenue
            "estimated_value": "float",  # Estimated value (USD)
            "source": "string",  # Data source
            "confidence": "string",  # Confidence level
        }

    @staticmethod
    def position_properties():
        """Position relationship properties (weight, etc)."""
        return {
            "weight": "float",  # Portfolio weight (%)
        }


class SchemaInitializer:
    """Initializes graph database schema."""

    @staticmethod
    def get_schema_statements():
        """Get all schema initialization statements.

        Returns:
            Dict with statement categories
        """
        return {
            "indexes": IndexDefinition.get_indexes(),
            "constraints": ConstraintDefinition.get_constraints(),
        }

    @staticmethod
    def get_node_labels():
        """Get all node labels used in schema.

        Returns:
            List of node label strings
        """
        return [
            NodeLabel.PORTFOLIO,
            NodeLabel.POSITION,
            NodeLabel.COMPANY,
            NodeLabel.COUNTRY,
            NodeLabel.REGION,
            NodeLabel.EXECUTIVE,
            NodeLabel.STOCK,
            NodeLabel.BOND,
            NodeLabel.DERIVATIVE,
        ]

    @staticmethod
    def get_relationship_types():
        """Get all relationship types used in schema.

        Returns:
            List of relationship type strings
        """
        return [
            RelationshipType.CONTAINS,
            RelationshipType.INVESTED_IN,
            RelationshipType.HOLDS,
            RelationshipType.ISSUED_BY,
            RelationshipType.HAS_SUBSIDIARY,
            RelationshipType.SUBSIDIARY_OF,
            RelationshipType.PARENT_OF,
            RelationshipType.HEADQUARTERED_IN,
            RelationshipType.OPERATES_IN,
            RelationshipType.SUPPLIES_TO,
            RelationshipType.CUSTOMER_OF,
            RelationshipType.CEO_OF,
            RelationshipType.LEADS,
            RelationshipType.PART_OF,
        ]

    @staticmethod
    def print_schema_summary():
        """Print summary of schema to logger."""
        logger.info("=== FIBO Graph Database Schema ===")
        logger.info(f"Node Labels: {len(SchemaInitializer.get_node_labels())}")
        for label in SchemaInitializer.get_node_labels():
            logger.debug(f"  - {label}")

        logger.info(f"Relationship Types: {len(SchemaInitializer.get_relationship_types())}")
        for rel_type in SchemaInitializer.get_relationship_types():
            logger.debug(f"  - {rel_type}")

        indexes = IndexDefinition.get_indexes()
        logger.info(f"Indexes: {len(indexes)}")
        for idx in indexes:
            logger.debug(f"  - {idx}")
