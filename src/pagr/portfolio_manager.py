"""Portfolio management and CRUD operations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages portfolio operations including listing and deletion."""

    def __init__(self, memgraph_client):
        """Initialize portfolio manager with Memgraph client.

        Args:
            memgraph_client: MemgraphClient instance for database operations
        """
        self.memgraph_client = memgraph_client

    def list_portfolios(self) -> List[Dict[str, Any]]:
        """Query all portfolios from database.

        Returns:
            List of portfolio dicts with keys: name, created_at, node_count
            Empty list if no portfolios or error occurs

        Example:
            [
                {"name": "Portfolio1", "created_at": "2024-01-15T10:30:00", "node_count": 25},
                {"name": "Portfolio2", "created_at": "2024-01-16T14:20:00", "node_count": 18}
            ]
        """
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            # Query to get all portfolios with metadata
            query = """
            MATCH (p:Portfolio)
            RETURN p.name AS name, p.created_at AS created_at
            ORDER BY p.name
            """

            results = self.memgraph_client.execute_query(query)
            logger.debug(f"Query results type: {type(results)}, length: {len(results) if results else 0}")

            # Convert results to list of dicts
            portfolios = []
            for i, record in enumerate(results):
                logger.debug(f"Record {i}: type={type(record)}, content={record}")

                # Handle both dict and record-like objects
                if isinstance(record, dict):
                    name = record.get("name", "Unknown")
                    created_at = record.get("created_at", "")
                else:
                    # Try to access as record attributes
                    name = getattr(record, "name", record.get("name", "Unknown") if hasattr(record, "get") else "Unknown")
                    created_at = getattr(record, "created_at", record.get("created_at", "") if hasattr(record, "get") else "")

                portfolio = {
                    "name": name,
                    "created_at": created_at,
                    "position_count": 0
                }
                portfolios.append(portfolio)
                logger.debug(f"Added portfolio: {portfolio}")

            logger.info(f"Listed {len(portfolios)} portfolios from database: {portfolios}")
            return portfolios

        except Exception as e:
            logger.error(f"Failed to list portfolios: {e}")
            return []

    def delete_portfolio(self, portfolio_name: str) -> bool:
        """Delete portfolio and all related data from database.

        Args:
            portfolio_name: Name of portfolio to delete

        Returns:
            True if successfully deleted, False if error or not found
        """
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            # Query to delete portfolio and all related nodes/relationships
            # This uses DETACH DELETE to cascade delete all relationships
            query = """
                MATCH (p:Portfolio {name: $portfolio_name})
                DETACH DELETE p
            """

            parameters = {"portfolio_name": portfolio_name}
            self.memgraph_client.execute_query(query, parameters)

            logger.info(f"Successfully deleted portfolio: {portfolio_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete portfolio '{portfolio_name}': {e}")
            return False

    def get_portfolio_metadata(self, portfolio_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific portfolio.

        Args:
            portfolio_name: Name of portfolio

        Returns:
            Dict with portfolio metadata or None if not found

        Example:
            {
                "name": "Portfolio1",
                "created_at": "2024-01-15T10:30:00",
                "position_count": 25,
                "company_count": 20,
                "country_count": 5
            }
        """
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            # Query to get basic portfolio metadata
            query = """
            MATCH (p:Portfolio {name: $portfolio_name})
            RETURN p.name AS name, p.created_at AS created_at
            LIMIT 1
            """

            parameters = {"portfolio_name": portfolio_name}
            results = self.memgraph_client.execute_query(query, parameters)

            if not results:
                logger.warning(f"Portfolio not found: {portfolio_name}")
                return None

            record = results[0]
            metadata = {
                "name": record.get("name", "Unknown"),
                "created_at": record.get("created_at", "")
            }

            logger.info(f"Retrieved metadata for portfolio: {portfolio_name}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to get portfolio metadata for '{portfolio_name}': {e}")
            return None

    def count_portfolios(self) -> int:
        """Get total count of portfolios in database.

        Returns:
            Number of portfolios, or 0 if error
        """
        try:
            portfolios = self.list_portfolios()
            return len(portfolios)
        except Exception as e:
            logger.error(f"Failed to count portfolios: {e}")
            return 0
