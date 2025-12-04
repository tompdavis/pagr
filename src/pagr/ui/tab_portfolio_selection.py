"""Portfolio Selection tab UI component."""

import streamlit as st
import logging
from pathlib import Path

from pagr.session_manager import SessionManager
from pagr.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


def display_portfolio_selection_tab(etl_manager, portfolio_manager: PortfolioManager):
    """Display portfolio selection and management tab.

    Args:
        etl_manager: ETLManager instance
        portfolio_manager: PortfolioManager instance
    """
    st.markdown("""
    Upload a new portfolio or manage existing portfolios in the database.
    The database is the system of record - portfolios persist even if the app is restarted.
    """)

    # Refresh portfolio list from database on tab load (database is system of record)
    _refresh_portfolio_list(portfolio_manager)

    st.divider()

    # Add Portfolio Section
    st.subheader("Add Portfolio")

    # Create two columns for better layout
    col1, col2 = st.columns([1, 3])

    with col1:
        add_method = st.selectbox(
            "Portfolio Source",
            ["CSV from Disk", "OFDB from FactSet"],
            help="Choose where to import your portfolio from"
        )

    if add_method == "CSV from Disk":
        with col2:
            st.empty()  # Placeholder for alignment

        # File uploader
        uploaded_file = st.file_uploader(
            "Upload Portfolio CSV",
            type="csv",
            help="CSV format: ticker,quantity,book_value,security_type (optional),isin (optional),cusip (optional)"
        )

        if uploaded_file is not None:
            current_file = SessionManager.get_current_file()

            if current_file != uploaded_file.name:
                SessionManager.set_current_file(uploaded_file.name)

                # Extract portfolio name from CSV filename (before ETL)
                portfolio_name = Path(uploaded_file.name).stem

                # Check if portfolio already exists in database
                try:
                    existing_portfolios = portfolio_manager.list_portfolios()
                    existing_names = [p.get("name") for p in existing_portfolios]

                    if portfolio_name in existing_names:
                        st.error(
                            f"❌ Portfolio '{portfolio_name}' already exists. "
                            f"Please delete it first or rename your CSV file."
                        )
                        logger.warning(f"Attempted to upload duplicate portfolio: {portfolio_name}")
                        SessionManager.set_current_file(None)
                    else:
                        # Portfolio name is unique, proceed with ETL
                        with st.spinner("Processing portfolio through ETL pipeline..."):
                            try:
                                # Check Memgraph connection
                                if not etl_manager.check_connection():
                                    st.error(
                                        "Cannot connect to Memgraph database. "
                                        "Please ensure Memgraph is running on 127.0.0.1:7687"
                                    )
                                else:
                                    # Process CSV
                                    portfolio, stats = etl_manager.process_uploaded_csv(uploaded_file)
                                    logger.info(f"Portfolio object created: name={portfolio.name}, positions={len(portfolio.positions)}")

                                    SessionManager.set_portfolio(portfolio, stats)
                                    SessionManager.set_query_service(etl_manager.query_service)

                                    logger.info(f"Portfolio stored in session state. Retrieving to verify...")
                                    stored_portfolio = SessionManager.get_portfolio()
                                    logger.info(f"Verification: retrieved portfolio = {stored_portfolio.name if stored_portfolio else 'NONE'}")

                                    # Show success message
                                    st.success(f"✅ Portfolio '{portfolio.name}' successfully loaded!")

                                    # Show pipeline statistics in expander
                                    with st.expander("Pipeline Statistics", expanded=False):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric("Positions Loaded", stats.positions_loaded)
                                            st.metric("Companies Enriched", stats.companies_enriched)
                                            st.metric("Companies Failed", stats.companies_failed)
                                        with col2:
                                            st.metric("Executives", stats.executives_enriched)
                                            st.metric("Countries", stats.countries_enriched)
                                            st.metric("Graph Nodes", stats.graph_nodes_created)

                                        if stats.errors:
                                            with st.expander("Errors"):
                                                for error in stats.errors[:5]:
                                                    st.warning(error)

                                    # Refresh portfolio list
                                    _refresh_portfolio_list(portfolio_manager)
                                    st.rerun()

                            except Exception as e:
                                st.error(f"Error processing portfolio: {str(e)}")
                                logger.exception(f"Portfolio processing error: {e}")

                except Exception as e:
                    st.error(f"Error checking for duplicate portfolios: {str(e)}")
                    logger.exception(f"Duplicate check error: {e}")

    else:  # OFDB from FactSet
        st.warning("🚧 OFDB import from FactSet is not implemented yet. This feature will be available in a future release.")

    st.divider()

    # Portfolio Management Section
    st.subheader("Manage Portfolios")

    # Refresh button
    if st.button("🔄 Refresh Portfolio List", use_container_width=True):
        _refresh_portfolio_list(portfolio_manager)
        st.rerun()

    # Clear All button
    if st.button("🗑️ Clear All Portfolios", use_container_width=True, type="secondary"):
        # Store flag in session state to show confirmation
        st.session_state["show_clear_all_confirm"] = True

    # Confirmation dialog
    if st.session_state.get("show_clear_all_confirm", False):
        st.warning("⚠️ This will delete ALL portfolios and positions. Reference data (companies, countries) will be preserved.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✓ Confirm Clear All", use_container_width=True, type="primary"):
                with st.spinner("Clearing all portfolios..."):
                    try:
                        if portfolio_manager.delete_all_portfolios():
                            st.success("✅ All portfolios cleared successfully!")
                            _refresh_portfolio_list(portfolio_manager)
                            # Clear session state
                            SessionManager.set_portfolio(None, None)
                            SessionManager.set_selected_portfolios([])
                            st.session_state["show_clear_all_confirm"] = False
                            st.rerun()
                        else:
                            st.error("Failed to clear portfolios")
                    except Exception as e:
                        st.error(f"Error clearing portfolios: {str(e)}")
                        logger.exception(f"Clear all error: {e}")

        with col2:
            if st.button("✗ Cancel", use_container_width=True):
                st.session_state["show_clear_all_confirm"] = False
                st.rerun()

    st.divider()

    # Get and display available portfolios
    available_portfolios = SessionManager.get_available_portfolios()

    if not available_portfolios:
        # Try to refresh if empty
        _refresh_portfolio_list(portfolio_manager)
        available_portfolios = SessionManager.get_available_portfolios()

    if available_portfolios:
        st.write(f"**Found {len(available_portfolios)} portfolio(s):**")

        for portfolio in available_portfolios:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                portfolio_name = portfolio.get("name", "Unknown")
                created_at = portfolio.get("created_at", "N/A")
                position_count = portfolio.get("position_count", 0)

                st.write(f"**{portfolio_name}**")
                st.caption(f"Positions: {position_count} | Created: {created_at}")

            with col2:
                st.empty()  # Spacer

            with col3:
                st.empty()  # Spacer

            with col4:
                # Delete button
                delete_key = f"delete_{portfolio_name}"
                if st.button("🗑️ Delete", key=delete_key, use_container_width=True):
                    # Show confirmation
                    col_confirm1, col_confirm2 = st.columns(2)

                    with col_confirm1:
                        if st.button(
                            "✓ Confirm Delete",
                            key=f"confirm_delete_{portfolio_name}",
                            use_container_width=True
                        ):
                            with st.spinner(f"Deleting portfolio '{portfolio_name}'..."):
                                try:
                                    if portfolio_manager.delete_portfolio(portfolio_name):
                                        st.success(f"✅ Portfolio '{portfolio_name}' deleted successfully!")
                                        _refresh_portfolio_list(portfolio_manager)
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to delete portfolio '{portfolio_name}'")
                                except Exception as e:
                                    st.error(f"Error deleting portfolio: {str(e)}")
                                    logger.exception(f"Delete portfolio error: {e}")

                    with col_confirm2:
                        if st.button(
                            "✗ Cancel",
                            key=f"cancel_delete_{portfolio_name}",
                            use_container_width=True
                        ):
                            st.info("Delete cancelled")

            st.divider()

    else:
        st.info("📌 No portfolios found. Upload a CSV portfolio to get started!")


def _refresh_portfolio_list(portfolio_manager: PortfolioManager):
    """Refresh the list of available portfolios from database.

    This stores the portfolio list in session state so it persists across tabs.
    The database is the system of record - portfolios persist even if the app
    is restarted.

    Args:
        portfolio_manager: PortfolioManager instance
    """
    try:
        portfolios = portfolio_manager.list_portfolios()
        SessionManager.set_available_portfolios(portfolios)
        logger.info(f"Refreshed portfolio list from database: {len(portfolios)} portfolios found")
        logger.debug(f"Available portfolios: {portfolios}")
    except Exception as e:
        logger.error(f"Error refreshing portfolio list: {e}")
        st.warning(f"Could not refresh portfolio list: {e}")
