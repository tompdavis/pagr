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
