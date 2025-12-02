"""Memgraph database client wrapper."""

import logging
from typing import Any, List, Optional, Dict

logger = logging.getLogger(__name__)


class MemgraphConnectionError(Exception):
    """Raised when connection to Memgraph fails."""

    pass


class MemgraphQueryError(Exception):
    """Raised when Cypher query execution fails."""

    pass


class MemgraphClient:
    """Memgraph database client with connection pooling and batch operations.

    This is a mock implementation that can be swapped with real gqlalchemy
    when it's installed. For now, it provides the interface we need.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7687,
        username: str = "",
        password: str = "",
        encrypted: bool = False,
    ):
        """Initialize Memgraph client.

        Args:
            host: Memgraph host
            port: Memgraph port
            username: Optional username
            password: Optional password
            encrypted: Whether to use encrypted connection
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.encrypted = encrypted
        self.is_connected = False
        self._connection = None
        self._cursor = None

        logger.info(
            f"Initialized Memgraph client for {host}:{port} "
            f"{'(encrypted)' if encrypted else '(unencrypted)'}"
        )

    def connect(self) -> None:
        """Establish connection to Memgraph.

        Raises:
            MemgraphConnectionError: If connection fails
        """
        try:
            from neo4j import GraphDatabase

            connection_string = f"bolt://{self.host}:{self.port}"
            if self.username and self.password:
                self._connection = GraphDatabase.driver(
                    connection_string,
                    auth=(self.username, self.password),
                    encrypted=self.encrypted,
                )
            else:
                self._connection = GraphDatabase.driver(
                    connection_string,
                    encrypted=self.encrypted,
                )

            # Test connection
            with self._connection.session() as session:
                session.run("RETURN 1 as num")

            self.is_connected = True
            logger.info(f"Connected to Memgraph at {self.host}:{self.port}")

        except ImportError as e:
            logger.error(f"neo4j driver not installed: {e}")
            raise MemgraphConnectionError(f"neo4j driver not found: {e}") from e
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise MemgraphConnectionError(f"Connection failed: {e}") from e

    def disconnect(self) -> None:
        """Close connection to Memgraph."""
        if self._connection:
            try:
                self._connection.close()
                self.is_connected = False
                logger.info("Disconnected from Memgraph")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)

        Returns:
            List of result records as dicts

        Raises:
            MemgraphQueryError: If query execution fails
        """
        if not self.is_connected:
            raise MemgraphConnectionError("Not connected to Memgraph. Call connect() first.")

        try:
            if self._connection is None:
                # Mock mode - log and return empty
                logger.debug(f"Mock: Executing query: {query[:100]}...")
                return []

            with self._connection.session() as session:
                result = session.run(query, parameters or {})
                records = [dict(record) for record in result]
                logger.debug(f"Query returned {len(records)} records")
                return records

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise MemgraphQueryError(f"Query failed: {e}") from e

    def execute_batch(self, queries: List[str]) -> bool:
        """Execute multiple Cypher queries in batch.

        Args:
            queries: List of Cypher query strings

        Returns:
            True if all queries succeeded

        Raises:
            MemgraphQueryError: If any query fails
        """
        if not self.is_connected:
            raise MemgraphConnectionError("Not connected to Memgraph. Call connect() first.")

        try:
            if self._connection is None:
                # Mock mode
                logger.debug(f"Mock: Executing {len(queries)} queries")
                return True

            with self._connection.session() as session:
                for query in queries:
                    session.run(query)
                logger.info(f"Successfully executed {len(queries)} queries")
                return True

        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise MemgraphQueryError(f"Batch failed: {e}") from e

    def clear_database(self, confirm: bool = False) -> None:
        """Delete all data from database (WARNING: destructive operation).

        Args:
            confirm: Must be True to prevent accidental deletion

        Raises:
            MemgraphConnectionError: If not connected
            ValueError: If confirm is not True
        """
        if not confirm:
            raise ValueError(
                "Database deletion requires confirm=True. "
                "This is a destructive operation!"
            )

        if not self.is_connected:
            raise MemgraphConnectionError("Not connected to Memgraph. Call connect() first.")

        try:
            logger.warning("Clearing all data from Memgraph database...")

            if self._connection is None:
                # Mock mode
                logger.debug("Mock: Database cleared")
                return

            with self._connection.session() as session:
                session.run("MATCH (n) DETACH DELETE n;")
                logger.info("Database cleared successfully")

        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            raise MemgraphQueryError(f"Clear failed: {e}") from e

    def get_node_count(self) -> int:
        """Get total number of nodes in database.

        Returns:
            Number of nodes
        """
        try:
            results = self.execute_query("MATCH (n) RETURN count(n) as count;")
            if results:
                return results[0].get("count", 0)
            return 0
        except Exception as e:
            logger.error(f"Failed to get node count: {e}")
            return 0

    def get_relationship_count(self) -> int:
        """Get total number of relationships in database.

        Returns:
            Number of relationships
        """
        try:
            results = self.execute_query("MATCH ()-[r]-() RETURN count(r) as count;")
            if results:
                return results[0].get("count", 0)
            return 0
        except Exception as e:
            logger.error(f"Failed to get relationship count: {e}")
            return 0

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with node count, relationship count, and labels
        """
        try:
            stats = {
                "nodes": self.get_node_count(),
                "relationships": self.get_relationship_count(),
            }

            # Try to get node labels (Neo4j syntax - Memgraph may not support this)
            try:
                label_results = self.execute_query(
                    "CALL db.labels() YIELD label RETURN COLLECT(label) as labels;"
                )
                if label_results:
                    stats["labels"] = label_results[0].get("labels", [])
            except Exception:
                # Memgraph doesn't have db.labels(), try alternative query
                try:
                    label_results = self.execute_query(
                        "MATCH (n) RETURN DISTINCT labels(n) as all_labels LIMIT 1000"
                    )
                    all_labels = set()
                    for result in label_results:
                        if "all_labels" in result:
                            all_labels.update(result["all_labels"])
                    stats["labels"] = list(all_labels)
                except Exception as e:
                    logger.debug(f"Could not fetch labels: {e}")
                    stats["labels"] = []

            # Try to get relationship types (Neo4j syntax - Memgraph may not support this)
            try:
                rel_results = self.execute_query(
                    "CALL db.relationshipTypes() YIELD relationshipType "
                    "RETURN COLLECT(relationshipType) as types;"
                )
                if rel_results:
                    stats["relationship_types"] = rel_results[0].get("types", [])
            except Exception:
                # Memgraph doesn't have db.relationshipTypes(), try alternative query
                try:
                    rel_results = self.execute_query(
                        "MATCH ()-[r]-() RETURN DISTINCT type(r) as rel_type LIMIT 1000"
                    )
                    rel_types = [r["rel_type"] for r in rel_results if "rel_type" in r]
                    stats["relationship_types"] = rel_types
                except Exception as e:
                    logger.debug(f"Could not fetch relationship types: {e}")
                    stats["relationship_types"] = []

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"nodes": 0, "relationships": 0, "labels": [], "relationship_types": []}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected else "disconnected"
        return f"MemgraphClient({self.host}:{self.port}, {status})"
