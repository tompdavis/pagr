"""Reusable portfolio selector UI component for multi-portfolio workflows.

This component is used by multiple tabs (Holdings, Chat Agent) to provide
consistent portfolio selection functionality.
"""

import streamlit as st
import logging
from typing import List, Dict, Tuple
from pagr.session_manager import SessionManager
from pagr.session_state import SessionStateKeys

logger = logging.getLogger(__name__)


def display_portfolio_selector(
    available_portfolios: List[Dict],
    column_width: Tuple[int, int] = None,
    show_stats: bool = True,
    key_prefix: str = "portfolio_selector",
) -> List[str]:
    """Display portfolio selector UI component.

    Displays a list of available portfolios with checkboxes and provides
    Select All / Deselect All buttons. Automatically updates session state
    when selections change.

    Args:
        available_portfolios: List of portfolio dicts with keys: name, created_at, position_count
        column_width: Tuple of (left_column_width, right_column_width) for layout. If None, render inline without columns.
        show_stats: If True, display position count and creation date
        key_prefix: Prefix for widget keys to ensure uniqueness across multiple uses

    Returns:
        List of currently selected portfolio names
    """
    # Create columns only if column_width is specified
    create_columns = column_width is not None

    if create_columns:
        left_col_width, right_col_width = column_width
        left_col, right_col = st.columns([left_col_width, right_col_width])
        selector_container = left_col
    else:
        # If no column_width specified, render inline
        selector_container = st.container()

    with selector_container:
        st.subheader("Portfolios")

        st.write(f"**Found {len(available_portfolios)} portfolio(s)**")

        # Select All / Deselect All buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "✓ Select All",
                use_container_width=True,
                key=f"{key_prefix}_select_all",
            ):
                portfolio_names = [p.get("name") for p in available_portfolios if p.get("name")]
                SessionManager.set_selected_portfolios(portfolio_names)
                logger.info(f"Selected all portfolios: {portfolio_names}")
                st.rerun()

        with col2:
            if st.button(
                "✗ Deselect All",
                use_container_width=True,
                key=f"{key_prefix}_deselect_all",
            ):
                SessionManager.set_selected_portfolios([])
                logger.info("Deselected all portfolios")
                st.rerun()

        st.divider()

        # Get currently selected portfolios
        selected_portfolios = SessionManager.get_selected_portfolios()

        # Auto-select portfolios ONLY on first app load (not on tab switches)
        if not SessionManager.portfolios_already_auto_selected() and available_portfolios:
            auto_selected = [p.get("name") for p in available_portfolios if p.get("name")]
            SessionManager.set_selected_portfolios(auto_selected)
            SessionManager.mark_portfolios_auto_selected()
            logger.info(f"Auto-selected portfolios on first load: {auto_selected}")
            st.rerun()

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
                    key=f"{key_prefix}_checkbox_{portfolio_name}",
                ):
                    new_selected.append(portfolio_name)

                if show_stats:
                    if created_at:
                        st.caption(f"Created: {created_at[:10]}")
                st.divider()

            # Update selected portfolios if changed
            if new_selected != selected_portfolios:
                SessionManager.set_selected_portfolios(new_selected)
                logger.info(f"Portfolio selection changed to: {new_selected}")
                st.rerun()
        else:
            st.warning("No portfolios found")

    return SessionManager.get_selected_portfolios()
