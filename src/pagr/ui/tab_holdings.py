"""Holdings View tab UI component."""

import streamlit as st
import logging
from typing import List

from pagr.session_manager import SessionManager
from pagr.portfolio_manager import PortfolioManager
from pagr.portfolio_loader import PortfolioLoader
from pagr.portfolio_analysis_service import PortfolioAnalysisService
from pagr.ui.metrics import display_portfolio_metrics
from pagr.ui.tabular import display_tabular_view
from pagr.ui.components import display_portfolio_selector

logger = logging.getLogger(__name__)


def display_holdings_tab(etl_manager, portfolio_manager: PortfolioManager):
    """Display holdings view with portfolio selection and analysis.

    Args:
        etl_manager: ETLManager instance
        portfolio_manager: PortfolioManager instance
    """
    # Initialize loaders and services
    portfolio_loader = PortfolioLoader(portfolio_manager)

    # Ensure query service is initialized
    query_service = SessionManager.get_query_service()
    if query_service is None:
        try:
            query_service = etl_manager.query_service
            SessionManager.set_query_service(query_service)
            logger.info("Query service initialized on tab load")
        except Exception as e:
            logger.warning(f"Could not initialize query service on tab load: {e}")

    # Initialize analysis service if query service is available
    analysis_service = None
    if query_service:
        analysis_service = PortfolioAnalysisService(query_service)

    # Get and refresh available portfolios from database
    try:
        available_portfolios = portfolio_loader.get_available_portfolios(force_refresh=True)

        if not available_portfolios:
            st.error("❌ No portfolios found in database!")
            st.info("📌 Please go to **Portfolio Selection tab** and upload a portfolio CSV file.")
            return

        logger.info(f"Available portfolios in Holdings View: {[p.get('name') for p in available_portfolios]}")

    except Exception as e:
        logger.error(f"Error loading portfolios: {e}")
        st.error(f"❌ Error loading portfolios: {e}")
        return

    # Two-column layout: Portfolio selector (left) + Holdings display (right)
    left_col, right_col = st.columns([1, 4])

    with left_col:
        selected_portfolios = display_portfolio_selector(
            available_portfolios,
            column_width=None,
            key_prefix="holdings_portfolio_selector",
        )

    with right_col:
        # Display selected portfolio(s)
        if not selected_portfolios:
            st.info("Please select at least one portfolio to view holdings.")
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
            header = f"Combined Portfolio View ({len(display_portfolios)} portfolios selected)"
        else:
            header = f"Portfolio: {display_portfolios[0].name}"

        st.subheader(header)

        # Display portfolio metrics (aggregated across all selected portfolios)
        display_portfolio_metrics(display_portfolios)

        # DEBUG: Log portfolio state
        total_positions = sum(len(p.positions) if p.positions else 0 for p in display_portfolios)
        logger.info(f"Display portfolios: {[p.name for p in display_portfolios]}, total positions: {total_positions}")
        for portfolio in display_portfolios[:1]:  # Log first portfolio
            if portfolio.positions:
                for i, pos in enumerate(portfolio.positions[:3]):  # Log first 3 positions
                    logger.debug(f"Position {i}: ticker={pos.ticker}, qty={pos.quantity}, book_value={pos.book_value}")

        st.divider()

        # Display tabular view
        query_service = SessionManager.get_query_service()

        if query_service:
            try:
                portfolio_names = [p.name for p in display_portfolios]
                logger.debug(f"Calling display_tabular_view with portfolios: {portfolio_names}, total positions: {total_positions}")
                display_tabular_view(display_portfolios, query_service)
            except Exception as e:
                st.error(f"Error displaying tabular view: {str(e)}")
                logger.exception(f"Tabular view error: {e}")
        else:
            st.error("Query service not initialized. Please reload the portfolio.")
