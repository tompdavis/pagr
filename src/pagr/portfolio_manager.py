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

            # Query to get all portfolios with metadata including position count
            query = """
            MATCH (p:Portfolio)
            OPTIONAL MATCH (p)-[:CONTAINS]->(pos:Position)
            WITH p.name AS name, p.created_at AS created_at, count(pos) AS position_count
            RETURN name, created_at, position_count
            ORDER BY name
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
                    position_count = record.get("position_count", 0)
                else:
                    # Try to access as record attributes
                    name = getattr(record, "name", record.get("name", "Unknown") if hasattr(record, "get") else "Unknown")
                    created_at = getattr(record, "created_at", record.get("created_at", "") if hasattr(record, "get") else "")
                    position_count = getattr(record, "position_count", record.get("position_count", 0) if hasattr(record, "get") else 0)

                portfolio = {
                    "name": name,
                    "created_at": created_at,
                    "position_count": position_count
                }
                portfolios.append(portfolio)
                logger.debug(f"Added portfolio: {portfolio}")

            logger.info(f"Listed {len(portfolios)} portfolios from database: {portfolios}")
            return portfolios

        except Exception as e:
            logger.error(f"Failed to list portfolios: {e}")
            return []

    def delete_portfolio(self, portfolio_name: str) -> bool:
        """Delete portfolio and all related positions from database.

        Removes the Portfolio node and all its Position nodes (which are portfolio-specific).
        Preserves Company, Country, Stock, and Bond nodes (which are shared across portfolios).

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
            # Explicitly delete Position nodes (which are portfolio-specific)
            # Preserves Stock, Bond, Company, Country nodes (which are shared)
            query = """
                MATCH (p:Portfolio {name: $portfolio_name})-[:CONTAINS]->(pos:Position)
                DETACH DELETE p, pos
            """

            parameters = {"portfolio_name": portfolio_name}
            self.memgraph_client.execute_query(query, parameters)

            logger.info(f"Successfully deleted portfolio: {portfolio_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete portfolio '{portfolio_name}': {e}")
            return False

    def delete_all_portfolios(self) -> bool:
        """Delete all data from the database (complete wipe).

        Removes ALL nodes: Portfolio, Position, Company, Country, Stock, Bond, Executive.
        This is a complete database reset.

        Returns:
            True if successfully deleted, False if error
        """
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            # Query to delete ALL nodes and relationships in the database
            query = """
                MATCH (n)
                DETACH DELETE n
            """

            self.memgraph_client.execute_query(query)

            logger.info("Successfully deleted all data from database (complete wipe)")
            return True

        except Exception as e:
            logger.error(f"Failed to delete all data: {e}")
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

    def reconstruct_portfolio_from_database(self, portfolio_name: str):
        """Reconstruct a full Portfolio object from the database.

        This allows portfolios to be accessed from the database without needing
        to be re-uploaded via CSV. The database is the system of record.

        Args:
            portfolio_name: Name of portfolio to reconstruct

        Returns:
            Portfolio object, or None if not found

        Note: This is a simplified reconstruction. For full reconstruction with all
        enriched data, we would need to traverse the entire graph and rebuild objects.
        For now, this creates a basic Portfolio with position data from the graph.
        """
        try:
            from pagr.fds.models.portfolio import Portfolio, Position

            logger.info(f"Starting reconstruction of portfolio: {portfolio_name}")

            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                logger.debug("Memgraph not connected, establishing connection...")
                self.memgraph_client.connect()

            # Query to get portfolio and its positions
            # Get all positions for the portfolio (don't filter by security presence)
            query = """
            MATCH (p:Portfolio {name: $portfolio_name})-[:CONTAINS]->(pos:Position)
            OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec)
            RETURN
                p.name AS portfolio_name,
                p.created_at AS created_at,
                pos.ticker AS ticker,
                pos.quantity AS quantity,
                pos.cost_basis AS cost_basis,
                pos.market_value AS market_value,
                pos.security_type AS security_type,
                pos.isin AS isin,
                pos.cusip AS cusip,
                pos.purchase_date AS purchase_date,
                sec.market_price AS market_price
            ORDER BY pos.ticker
            """

            logger.debug(f"Executing reconstruction query with parameter: portfolio_name={portfolio_name}")
            parameters = {"portfolio_name": portfolio_name}
            results = self.memgraph_client.execute_query(query, parameters)
            logger.debug(f"Query returned {len(results) if results else 0} results")

            if not results:
                logger.warning(f"No portfolio data found for: {portfolio_name}")
                return None

            # Create Portfolio object
            portfolio = Portfolio(name=portfolio_name)
            portfolio.created_at = results[0].get("created_at", "") if results else ""

            # Extract positions from results
            positions = []
            logger.debug(f"Processing {len(results)} records from database query")

            for i, record in enumerate(results):
                try:
                    logger.debug(f"Record {i}: {record}")

                    # Build position data with required fields having defaults
                    # Use cost_basis if available, fallback to book_value, then default to 0
                    cost_basis = record.get("cost_basis")
                    book_value = record.get("book_value")
                    final_book_value = cost_basis if cost_basis is not None else (book_value if book_value is not None else 0)

                    position_data = {
                        "ticker": record.get("ticker") or None,  # Can be None for bonds
                        "quantity": record.get("quantity", 0),
                        "book_value": final_book_value,
                        "security_type": record.get("security_type", "Unknown"),
                    }

                    # Add optional fields only if they have values
                    if record.get("isin"):
                        position_data["isin"] = record.get("isin")
                    if record.get("cusip"):
                        position_data["cusip"] = record.get("cusip")
                    if record.get("purchase_date"):
                        position_data["purchase_date"] = record.get("purchase_date")
                    if record.get("market_value") is not None:
                        position_data["market_value"] = record.get("market_value")

                    logger.debug(f"Position data: {position_data}")
                    logger.debug(f"About to create Position with: ticker={position_data.get('ticker')}, isin={position_data.get('isin')}, cusip={position_data.get('cusip')}, qty={position_data.get('quantity')}, book_value={position_data.get('book_value')}")

                    position = Position(**position_data)
                    positions.append(position)
                    logger.debug(f"Successfully created Position object: ticker={position.ticker}, qty={position.quantity}, book_value={position.book_value}")
                except ValueError as ve:
                    logger.error(f"ValueError creating Position from record {i}: {ve}. Data was: {position_data}", exc_info=True)
                    continue
                except Exception as e:
                    logger.error(f"Error reconstructing position from record {i}: {e}. Record: {record}", exc_info=True)
                    continue

            portfolio.positions = positions
            logger.debug(f"Portfolio has {len(positions)} positions before calculate_weights()")

            portfolio.calculate_weights()
            logger.debug(f"Portfolio has {len(portfolio.positions)} positions after calculate_weights()")

            logger.info(f"Reconstructed portfolio '{portfolio_name}' with {len(positions)} positions from database")
            return portfolio

        except Exception as e:
            logger.error(f"Failed to reconstruct portfolio '{portfolio_name}': {e}")
            return None

    def reconstruct_portfolios_from_database(self, portfolio_names: list):
        """Reconstruct multiple Portfolio objects from the database efficiently.

        This method loads multiple portfolios in a single query by filtering on multiple
        portfolio names, then groups the results by portfolio before creating Portfolio objects.

        Args:
            portfolio_names: List of portfolio names to reconstruct

        Returns:
            List of Portfolio objects (empty list if none found or error occurs)

        Note: This is more efficient than calling reconstruct_portfolio_from_database
        multiple times as it uses a single database query with WHERE...IN clause.
        """
        try:
            from pagr.fds.models.portfolio import Portfolio, Position

            logger.info(f"Starting reconstruction of {len(portfolio_names)} portfolios: {portfolio_names}")

            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                logger.debug("Memgraph not connected, establishing connection...")
                self.memgraph_client.connect()

            # Build parameter list for WHERE...IN clause
            # Query to get all positions for all specified portfolios in one go
            query = """
            MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)
            WHERE p.name IN $portfolio_names
            OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec)
            RETURN
                p.name AS portfolio_name,
                p.created_at AS created_at,
                pos.ticker AS ticker,
                pos.quantity AS quantity,
                pos.cost_basis AS cost_basis,
                pos.market_value AS market_value,
                pos.security_type AS security_type,
                pos.isin AS isin,
                pos.cusip AS cusip,
                pos.purchase_date AS purchase_date,
                sec.market_price AS market_price
            ORDER BY p.name, pos.ticker
            """

            logger.debug(f"Executing multi-portfolio reconstruction query for: {portfolio_names}")
            parameters = {"portfolio_names": portfolio_names}
            results = self.memgraph_client.execute_query(query, parameters)
            logger.debug(f"Query returned {len(results) if results else 0} results")

            if not results:
                logger.warning(f"No portfolio data found for: {portfolio_names}")
                return []

            # Group results by portfolio_name
            portfolios_dict = {}
            for record in results:
                p_name = record.get("portfolio_name")

                # Initialize portfolio entry if this is first record for this portfolio
                if p_name not in portfolios_dict:
                    portfolio = Portfolio(name=p_name)
                    portfolio.created_at = record.get("created_at", "")
                    portfolios_dict[p_name] = {
                        "portfolio": portfolio,
                        "records": []
                    }

                portfolios_dict[p_name]["records"].append(record)

            # Process each portfolio's records and create Position objects
            portfolios = []
            for p_name, data in portfolios_dict.items():
                portfolio = data["portfolio"]
                portfolio_records = data["records"]
                positions = []

                logger.debug(f"Processing {len(portfolio_records)} records for portfolio: {p_name}")

                for i, record in enumerate(portfolio_records):
                    try:
                        logger.debug(f"Record {i} for '{p_name}': {record}")

                        # Build position data with required fields having defaults
                        # Use cost_basis if available, fallback to book_value, then default to 0
                        cost_basis = record.get("cost_basis")
                        book_value = record.get("book_value")
                        final_book_value = cost_basis if cost_basis is not None else (book_value if book_value is not None else 0)

                        position_data = {
                            "ticker": record.get("ticker") or None,  # Can be None for bonds
                            "quantity": record.get("quantity", 0),
                            "book_value": final_book_value,
                            "security_type": record.get("security_type", "Unknown"),
                        }

                        # Add optional fields only if they have values
                        if record.get("isin"):
                            position_data["isin"] = record.get("isin")
                        if record.get("cusip"):
                            position_data["cusip"] = record.get("cusip")
                        if record.get("purchase_date"):
                            position_data["purchase_date"] = record.get("purchase_date")
                        if record.get("market_value") is not None:
                            position_data["market_value"] = record.get("market_value")

                        logger.debug(f"Position data: {position_data}")

                        position = Position(**position_data)
                        positions.append(position)
                        logger.debug(f"Successfully created Position: ticker={position.ticker}, qty={position.quantity}")

                    except ValueError as ve:
                        logger.error(f"ValueError creating Position for '{p_name}' from record {i}: {ve}. Data was: {position_data}", exc_info=True)
                        continue
                    except Exception as e:
                        logger.error(f"Error reconstructing position for '{p_name}' from record {i}: {e}. Record: {record}", exc_info=True)
                        continue

                portfolio.positions = positions
                logger.debug(f"Portfolio '{p_name}' has {len(positions)} positions before calculate_weights()")

                portfolio.calculate_weights()
                logger.debug(f"Portfolio '{p_name}' has {len(portfolio.positions)} positions after calculate_weights()")

                portfolios.append(portfolio)
                logger.info(f"Reconstructed portfolio '{p_name}' with {len(positions)} positions from database")

            logger.info(f"Successfully reconstructed {len(portfolios)} portfolios from database")
            return portfolios

        except Exception as e:
            logger.error(f"Failed to reconstruct portfolios {portfolio_names}: {e}")
            return []
