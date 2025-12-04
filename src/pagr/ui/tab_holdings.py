"""Holdings View tab UI component."""

import streamlit as st
import logging
from typing import List

from pagr.session_manager import SessionManager
from pagr.portfolio_manager import PortfolioManager
from pagr.ui.metrics import display_portfolio_metrics
from pagr.ui.tabular import display_tabular_view
from pagr.ui.graph_view import display_graph_view

logger = logging.getLogger(__name__)


def display_holdings_tab(etl_manager, portfolio_manager: PortfolioManager):
    """Display holdings view with portfolio selection and analysis.

    Args:
        etl_manager: ETLManager instance
        portfolio_manager: PortfolioManager instance
    """
    # Load current portfolio from session (loaded when CSV was uploaded)
    current_portfolio = SessionManager.get_portfolio()

    logger.info(f"Holdings View loading - current_portfolio type: {type(current_portfolio)}, value: {current_portfolio}")

    # If no portfolio in session, try to load the first one from database
    if current_portfolio is None:
        logger.info("No portfolio in session, attempting to load from database...")

        # Get portfolios from database
        try:
            portfolios = portfolio_manager.list_portfolios()
            if portfolios:
                first_portfolio_name = portfolios[0].get("name")
                logger.info(f"Found {len(portfolios)} portfolio(s) in database. Reconstructing: {first_portfolio_name}")

                # Reconstruct the Portfolio from database
                current_portfolio = portfolio_manager.reconstruct_portfolio_from_database(first_portfolio_name)

                if current_portfolio:
                    logger.info(f"Successfully reconstructed portfolio from database: {first_portfolio_name}")
                    SessionManager.set_portfolio(current_portfolio, None)

                    # Also set up the query service for graph queries
                    # The query service is needed for tabular/graph views
                    try:
                        query_service = etl_manager.query_service
                        SessionManager.set_query_service(query_service)
                        logger.info("Query service initialized for reconstructed portfolio")
                    except Exception as e:
                        logger.warning(f"Could not initialize query service: {e}")

                    # Auto-select this portfolio
                    SessionManager.set_selected_portfolios([first_portfolio_name])
                else:
                    st.error(f"❌ Failed to reconstruct portfolio '{first_portfolio_name}' from database")
                    return
            else:
                st.error("❌ No portfolios found in database!")
                st.info("📌 Please go to **Portfolio Selection tab** and upload a portfolio CSV file.")
                return
        except Exception as e:
            logger.error(f"Error loading portfolios from database: {e}")
            st.error(f"❌ Error loading portfolios from database: {e}")
            return

    # Ensure query service is initialized (needed for graph queries)
    query_service = SessionManager.get_query_service()
    if query_service is None:
        try:
            query_service = etl_manager.query_service
            SessionManager.set_query_service(query_service)
            logger.info("Query service initialized on tab load")
        except Exception as e:
            logger.warning(f"Could not initialize query service on tab load: {e}")

    # Always refresh available portfolios from database
    available_portfolios = []
    try:
        portfolios = portfolio_manager.list_portfolios()
        logger.info(f"Query returned {len(portfolios)} portfolios: {portfolios}")

        if portfolios:
            SessionManager.set_available_portfolios(portfolios)
            available_portfolios = portfolios
        else:
            logger.warning("Query returned no portfolios, using session state fallback")
            available_portfolios = SessionManager.get_available_portfolios()

        logger.info(f"Available portfolios in Holdings View: {available_portfolios}")
    except Exception as e:
        logger.error(f"Error loading portfolios: {e}")
        st.warning(f"Could not load portfolio list: {e}")
        available_portfolios = SessionManager.get_available_portfolios()

    # Ensure we at least have the current portfolio
    if not available_portfolios and current_portfolio:
        logger.warning(f"No portfolios found, using current portfolio: {current_portfolio.name}")
        available_portfolios = [{
            "name": current_portfolio.name,
            "created_at": current_portfolio.created_at or "",
            "position_count": len(current_portfolio.positions)
        }]

    # Two-column layout: Portfolio selector (left) + Holdings display (right)
    left_col, right_col = st.columns([1, 4])

    with left_col:
        st.subheader("Portfolios")

        st.write(f"**Found {len(available_portfolios)} portfolio(s)**")

        # Select All / Deselect All buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Select All", use_container_width=True, key="select_all"):
                portfolio_names = [p.get("name") for p in available_portfolios if p.get("name")]
                SessionManager.set_selected_portfolios(portfolio_names)
                st.rerun()

        with col2:
            if st.button("✗ Deselect All", use_container_width=True, key="deselect_all"):
                SessionManager.set_selected_portfolios([])
                st.rerun()

        st.divider()

        # Get selected portfolios from session
        selected_portfolios = SessionManager.get_selected_portfolios()

        # Auto-select portfolios if none selected yet
        if not selected_portfolios and available_portfolios:
            # Auto-select all available portfolios on first load
            auto_selected = [p.get("name") for p in available_portfolios if p.get("name")]
            SessionManager.set_selected_portfolios(auto_selected)
            selected_portfolios = auto_selected
            logger.info(f"Auto-selected portfolios: {auto_selected}")

        # Portfolio checkboxes
        new_selected = []

        if available_portfolios:
            for portfolio in available_portfolios:
                portfolio_name = portfolio.get("name", "Unknown")
                position_count = portfolio.get("position_count", 0)
                created_at = portfolio.get("created_at", "")

                is_checked = portfolio_name in selected_portfolios

                if st.checkbox(
                    f"{portfolio_name}",
                    value=is_checked,
                    key=f"portfolio_checkbox_{portfolio_name}"
                ):
                    new_selected.append(portfolio_name)

                if created_at:
                    st.caption(f"Created: {created_at[:10]}")
                st.divider()

            # Update selected portfolios if changed
            if new_selected != selected_portfolios:
                SessionManager.set_selected_portfolios(new_selected)
                st.rerun()
        else:
            st.warning("No portfolios found")

    with right_col:
        # Display selected portfolio(s)
        if not selected_portfolios:
            st.info("Please select at least one portfolio to view holdings.")
            return

        # Load portfolios for display
        is_multiple = len(selected_portfolios) > 1

        # Determine which portfolio objects to display
        display_portfolios = []

        if not is_multiple:
            # Single portfolio: use current or reconstruct from database
            if current_portfolio and current_portfolio.name == selected_portfolios[0]:
                display_portfolios = [current_portfolio]
            else:
                # Reconstruct single portfolio from database
                reconstructed = portfolio_manager.reconstruct_portfolio_from_database(selected_portfolios[0])
                if reconstructed:
                    display_portfolios = [reconstructed]
                    # Update session with reconstructed portfolio
                    SessionManager.set_portfolio(reconstructed, None)
                else:
                    st.error(f"❌ Failed to load portfolio '{selected_portfolios[0]}'")
                    return
        else:
            # Multiple portfolios: load all from database efficiently
            try:
                display_portfolios = portfolio_manager.reconstruct_portfolios_from_database(selected_portfolios)
                if not display_portfolios:
                    st.error(f"❌ Failed to load {len(selected_portfolios)} portfolios from database")
                    return
                logger.info(f"Loaded {len(display_portfolios)} portfolios from database")
            except Exception as e:
                logger.error(f"Error loading multiple portfolios: {e}")
                st.error(f"❌ Error loading portfolios: {e}")
                return

        # Portfolio header
        if is_multiple:
            header = f"Combined Portfolio View ({len(display_portfolios)} portfolios selected)"
        else:
            header = f"Portfolio: {display_portfolios[0].name}"

        st.subheader(header)

        # Display portfolio metrics (first portfolio for now, Phase 4 will add aggregation)
        display_portfolio_metrics(display_portfolios[0])

        # DEBUG: Log portfolio state
        total_positions = sum(len(p.positions) if p.positions else 0 for p in display_portfolios)
        logger.info(f"Display portfolios: {[p.name for p in display_portfolios]}, total positions: {total_positions}")
        for portfolio in display_portfolios[:1]:  # Log first portfolio
            if portfolio.positions:
                for i, pos in enumerate(portfolio.positions[:3]):  # Log first 3 positions
                    logger.debug(f"Position {i}: ticker={pos.ticker}, qty={pos.quantity}, book_value={pos.book_value}")

        st.divider()

        # View selection
        st.subheader("Display Options")

        view_selection = st.radio(
            "Select View",
            ["Tabular Analysis", "Graph Visualization"],
            horizontal=True,
            key="holdings_view_selection"
        )

        st.divider()

        # Display selected view
        query_service = SessionManager.get_query_service()

        if view_selection == "Tabular Analysis":
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

        elif view_selection == "Graph Visualization":
            try:
                display_graph_view(display_portfolios, etl_manager.memgraph_client)
            except Exception as e:
                st.error(f"Error displaying graph view: {str(e)}")
                logger.exception(f"Graph view error: {e}")
