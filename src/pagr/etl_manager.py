"""ETL pipeline manager for Streamlit app."""

import logging
from pathlib import Path
import tempfile
import streamlit as st

from pagr.fds.config import load_config
from pagr.fds.clients.factset_client import FactSetClient
from pagr.fds.clients.memgraph_client import MemgraphClient
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.graph.builder import GraphBuilder
from pagr.fds.services.pipeline import ETLPipeline
from pagr.fds.graph.queries import QueryService
from pagr.session_manager import PipelineStatistics

logger = logging.getLogger(__name__)


class ETLManager:
    """Manages ETL pipeline execution in Streamlit context."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize ETL manager with configuration."""
        try:
            self.config = load_config(config_path)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            self.config = None

        self._factset_client = None
        self._memgraph_client = None
        self._query_service = None

    @staticmethod
    def _read_factset_credentials(credentials_file: str) -> tuple[str, str]:
        """Read FactSet credentials from file.

        Args:
            credentials_file: Path to credentials file (fds-api.key)

        Returns:
            Tuple of (username, api_key)

        Raises:
            FileNotFoundError: If credentials file not found
            ValueError: If credentials are malformed
        """
        cred_path = Path(credentials_file)

        if not cred_path.exists():
            raise FileNotFoundError(
                f"FactSet credentials file not found: {credentials_file}. "
                f"Please create fds-api.key in the project root with:\n"
                f'  FDS_USERNAME="your_username"\n'
                f'  FDS_API_KEY="your_api_key"'
            )

        try:
            username = None
            api_key = None

            with open(cred_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FDS_USERNAME="):
                        username = line.split("=", 1)[1].strip().strip('"\'')
                    elif line.startswith("FDS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"\'')

            if not username or not api_key:
                raise ValueError(
                    f"Invalid credentials file format. Expected:\n"
                    f'  FDS_USERNAME="username"\n'
                    f'  FDS_API_KEY="apikey"'
                )

            logger.info(f"Loaded FactSet credentials for {username}")
            return username, api_key

        except Exception as e:
            logger.error(f"Error reading credentials file: {e}")
            raise

    @property
    def factset_client(self) -> FactSetClient:
        """Get or create FactSet client."""
        if self._factset_client is None:
            # Read FactSet credentials from file
            credentials_file = "fds-api.key"
            if self.config and hasattr(self.config, 'factset'):
                credentials_file = self.config.factset.credentials_file

            username, api_key = self._read_factset_credentials(credentials_file)

            self._factset_client = FactSetClient(
                username=username,
                api_key=api_key,
                rate_limit_rps=10
            )
        return self._factset_client

    @property
    def memgraph_client(self) -> MemgraphClient:
        """Get or create Memgraph client."""
        if self._memgraph_client is None:
            host = "localhost"
            port = 7687
            username = ""
            password = ""

            if self.config and hasattr(self.config, 'memgraph'):
                host = self.config.memgraph.host
                port = self.config.memgraph.port
                username = self.config.memgraph.username
                password = self.config.memgraph.password

            self._memgraph_client = MemgraphClient(
                host=host,
                port=port,
                username=username,
                password=password,
                encrypted=False
            )
        return self._memgraph_client

    @property
    def query_service(self) -> QueryService:
        """Get or create query service."""
        if self._query_service is None:
            self._query_service = QueryService(self.memgraph_client)
        return self._query_service

    def check_connection(self) -> bool:
        """Check if Memgraph is accessible."""
        try:
            # Connect if not already connected
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            self.memgraph_client.execute_query("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Memgraph connection error: {e}")
            return False

    def process_uploaded_csv(self, uploaded_file) -> tuple:
        """
        Process uploaded CSV through ETL pipeline.

        Args:
            uploaded_file: Streamlit uploaded file object

        Returns:
            Tuple of (Portfolio, PipelineStatistics)

        Raises:
            Exception: If processing fails
        """
        # Write uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            # Ensure Memgraph connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            portfolio_loader = PortfolioLoader()
            graph_builder = GraphBuilder()

            pipeline = ETLPipeline(
                factset_client=self.factset_client,
                portfolio_loader=portfolio_loader,
                graph_builder=graph_builder
            )

            # Execute ETL pipeline
            statements, stats = pipeline.execute(tmp_path)

            # Execute graph statements in Memgraph
            if statements:
                logger.info(f"Executing {len(statements)} graph statements")
                for stmt in statements:
                    try:
                        self.memgraph_client.execute_query(stmt)
                    except Exception as e:
                        logger.warning(f"Statement execution error: {e}")
                        stats.errors.append(str(e))

            # Load portfolio from CSV
            portfolio = portfolio_loader.load(tmp_path)

            logger.info(f"Pipeline complete: {stats.positions_loaded} positions, "
                       f"{stats.companies_enriched} companies enriched")

            return portfolio, stats

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def clear_database(self):
        """Clear all data from Memgraph database."""
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            logger.info("Clearing database")
            self.memgraph_client.execute_query("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            raise

    def setup_database_schema(self):
        """Set up database indexes for better query performance."""
        try:
            logger.info("Setting up database indexes")
            # Indexes are created by the GraphBuilder during graph creation
            # Additional optimization can be added here if needed
            logger.info("Database optimization configuration complete")
        except Exception as e:
            logger.warning(f"Schema setup issue: {e}")
            # Don't fail if schema setup has issues

    def get_database_stats(self) -> dict:
        """Get statistics about the database."""
        try:
            # Ensure connection is established
            if not self.memgraph_client.is_connected:
                self.memgraph_client.connect()

            stats = self.memgraph_client.get_database_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
