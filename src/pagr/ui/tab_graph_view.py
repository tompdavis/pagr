"""Graph View tab UI component."""

import streamlit as st
import logging

from pagr.session_manager import SessionManager
from pagr.portfolio_manager import PortfolioManager
from pagr.portfolio_loader import PortfolioLoader
from pagr.ui.graph_view import display_graph_view
from pagr.ui.components import display_portfolio_selector

logger = logging.getLogger(__name__)


def display_graph_view_tab(etl_manager, portfolio_manager: PortfolioManager):
    """Display graph visualization tab with portfolio selection.

    Args:
        etl_manager: ETLManager instance
        portfolio_manager: PortfolioManager instance
    """
    # Initialize loaders
    portfolio_loader = PortfolioLoader(portfolio_manager)

    # Get and refresh available portfolios from database
    try:
        available_portfolios = portfolio_loader.get_available_portfolios(force_refresh=True)

        if not available_portfolios:
            st.error("❌ No portfolios found in database!")
            st.info("📌 Please go to **Portfolio Selection tab** and upload a portfolio CSV file.")
            return

        logger.info(f"Available portfolios in Graph View: {[p.get('name') for p in available_portfolios]}")

    except Exception as e:
        logger.error(f"Error loading portfolios: {e}")
        st.error(f"❌ Error loading portfolios: {e}")
        return

    # Two-column layout: Portfolio selector (left) + Graph display (right)
    left_col, right_col = st.columns([1, 4])

    with left_col:
        selected_portfolios = display_portfolio_selector(
            available_portfolios,
            column_width=None,
            key_prefix="graph_view_portfolio_selector",
        )

    with right_col:
        # Display selected portfolio(s)
        if not selected_portfolios:
            st.info("Please select at least one portfolio to view the graph.")
            return

        # Load portfolios efficiently using loader
        try:
            display_portfolios = portfolio_loader.load_portfolios(selected_portfolios)

            if not display_portfolios:
                st.error(f"❌ Failed to load {len(selected_portfolios)} portfolios from database")
                return

            logger.info(f"Loaded {len(display_portfolios)} portfolios from database")

        except Exception as e:
            logger.error(f"Error loading portfolios: {e}")
            st.error(f"❌ Error loading portfolios: {e}")
            return

        # Portfolio header
        is_multiple = len(display_portfolios) > 1
        if is_multiple:
            header = f"Graph View ({len(display_portfolios)} portfolios selected)"
        else:
            header = f"Graph View: {display_portfolios[0].name}"

        st.subheader(header)
        st.divider()

        # Display graph view
        try:
            display_graph_view(display_portfolios, etl_manager.memgraph_client)
        except Exception as e:
            st.error(f"Error displaying graph view: {str(e)}")
            logger.exception(f"Graph view error: {e}")
