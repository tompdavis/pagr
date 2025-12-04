"""Streamlit session state manager for portfolio data."""

import streamlit as st
from typing import Optional
from pagr.fds.models.portfolio import Portfolio
from dataclasses import dataclass


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
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SessionManager:
    """Manages Streamlit session state for portfolio and ETL data."""

    @staticmethod
    def initialize():
        """Initialize session state variables if they don't exist."""
        if "portfolio" not in st.session_state:
            st.session_state.portfolio = None
        if "pipeline_stats" not in st.session_state:
            st.session_state.pipeline_stats = None
        if "graph_built" not in st.session_state:
            st.session_state.graph_built = False
        if "query_service" not in st.session_state:
            st.session_state.query_service = None
        if "current_file" not in st.session_state:
            st.session_state.current_file = None

        # NEW: Connection testing state
        if "connection_status" not in st.session_state:
            st.session_state.connection_status = {
                "memgraph": {"status": "untested", "message": ""},
                "factset": {"status": "untested", "message": ""},
                "llm": {"status": "not_implemented", "message": ""}
            }

        # NEW: Portfolio management
        if "available_portfolios" not in st.session_state:
            st.session_state.available_portfolios = []

        if "selected_portfolios" not in st.session_state:
            st.session_state.selected_portfolios = []

        # NEW: Settings state (loaded from config.yaml)
        if "settings" not in st.session_state:
            st.session_state.settings = None

        # NEW: Track if connections have been tested on startup
        if "connections_tested_on_startup" not in st.session_state:
            st.session_state.connections_tested_on_startup = False

    @staticmethod
    def set_portfolio(portfolio: Portfolio, stats: PipelineStatistics):
        """Set portfolio and pipeline statistics in session state."""
        st.session_state.portfolio = portfolio
        st.session_state.pipeline_stats = stats
        st.session_state.graph_built = True

    @staticmethod
    def get_portfolio() -> Optional[Portfolio]:
        """Get current portfolio from session state."""
        return st.session_state.get("portfolio")

    @staticmethod
    def get_pipeline_stats() -> Optional[PipelineStatistics]:
        """Get pipeline statistics from session state."""
        return st.session_state.get("pipeline_stats")

    @staticmethod
    def get_query_service():
        """Get query service from session state."""
        return st.session_state.get("query_service")

    @staticmethod
    def set_query_service(query_service):
        """Set query service in session state."""
        st.session_state.query_service = query_service

    @staticmethod
    def is_graph_built() -> bool:
        """Check if graph has been built."""
        return st.session_state.get("graph_built", False)

    @staticmethod
    def set_current_file(filename: str):
        """Set current file name in session state."""
        st.session_state.current_file = filename

    @staticmethod
    def get_current_file() -> Optional[str]:
        """Get current file name from session state."""
        return st.session_state.get("current_file")

    @staticmethod
    def clear():
        """Clear all session state variables."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        SessionManager.initialize()

    # NEW: Connection status management
    @staticmethod
    def set_connection_status(service: str, status: str, message: str):
        """Update connection status for a service.

        Args:
            service: Service name (memgraph, factset, llm)
            status: Status (success, error, not_implemented, untested)
            message: Status message
        """
        if service in st.session_state.connection_status:
            st.session_state.connection_status[service] = {
                "status": status,
                "message": message
            }

    @staticmethod
    def get_connection_status(service: str) -> dict:
        """Get connection status for a service.

        Args:
            service: Service name (memgraph, factset, llm)

        Returns:
            Dict with status and message
        """
        return st.session_state.connection_status.get(
            service,
            {"status": "untested", "message": ""}
        )

    @staticmethod
    def get_all_connection_status() -> dict:
        """Get connection status for all services.

        Returns:
            Dict with status for all services
        """
        return st.session_state.get("connection_status", {})

    # NEW: Portfolio management
    @staticmethod
    def set_available_portfolios(portfolios: list):
        """Set list of available portfolios.

        Args:
            portfolios: List of portfolio dicts with keys: name, created_at, position_count
        """
        st.session_state.available_portfolios = portfolios

    @staticmethod
    def get_available_portfolios() -> list:
        """Get list of available portfolios.

        Returns:
            List of portfolio dicts
        """
        return st.session_state.get("available_portfolios", [])

    @staticmethod
    def set_selected_portfolios(portfolio_names: list):
        """Set list of selected portfolio names.

        Args:
            portfolio_names: List of portfolio names to select
        """
        st.session_state.selected_portfolios = portfolio_names

    @staticmethod
    def get_selected_portfolios() -> list:
        """Get list of selected portfolio names.

        Returns:
            List of portfolio names
        """
        return st.session_state.get("selected_portfolios", [])

    @staticmethod
    def set_settings(settings: dict):
        """Set application settings.

        Args:
            settings: Settings dict loaded from config.yaml
        """
        st.session_state.settings = settings

    @staticmethod
    def get_settings() -> Optional[dict]:
        """Get application settings.

        Returns:
            Settings dict or None
        """
        return st.session_state.get("settings")

    @staticmethod
    def mark_connections_tested():
        """Mark that connections have been tested on startup."""
        st.session_state.connections_tested_on_startup = True

    @staticmethod
    def connections_already_tested() -> bool:
        """Check if connections have been tested on startup.

        Returns:
            True if already tested, False otherwise
        """
        return st.session_state.get("connections_tested_on_startup", False)
