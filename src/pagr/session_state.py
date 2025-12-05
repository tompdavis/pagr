"""Centralized session state constants and configuration.

This module provides constants for all session state keys used throughout
the application, replacing scattered magic strings with type-safe references.
"""

from enum import Enum


class SessionStateKeys(Enum):
    """Enumeration of all session state keys used in the application."""

    # Portfolio data
    PORTFOLIO = "portfolio"
    AVAILABLE_PORTFOLIOS = "available_portfolios"
    SELECTED_PORTFOLIOS = "selected_portfolios"
    RECONSTRUCTED_PORTFOLIOS = "reconstructed_portfolios"

    # Pipeline and ETL
    PIPELINE_STATS = "pipeline_stats"
    GRAPH_BUILT = "graph_built"
    CURRENT_FILE = "current_file"

    # Query service
    QUERY_SERVICE = "query_service"

    # Connection status
    CONNECTION_STATUS = "connection_status"
    CONNECTIONS_TESTED_ON_STARTUP = "connections_tested_on_startup"

    # Settings
    SETTINGS = "settings"

    # UI state - Portfolio Selection tab
    SHOW_CLEAR_ALL_CONFIRM = "show_clear_all_confirm"
    SHOW_DELETE_CONFIRM_PREFIX = "show_delete_confirm_"

    # UI state - Holdings tab
    HOLDINGS_VIEW_SELECTION = "holdings_view_selection"

    # UI state - Portfolio selector component
    PORTFOLIO_SELECTOR_EXPANDED = "portfolio_selector_expanded"


class SessionStateDefaults:
    """Default values for session state initialization."""

    CONNECTION_STATUS_TEMPLATE = {
        "memgraph": {"status": "untested", "message": ""},
        "factset": {"status": "untested", "message": ""},
        "llm": {"status": "not_implemented", "message": ""},
    }
