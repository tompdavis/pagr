"""Portfolio metrics display component."""

import streamlit as st
from pagr.fds.models.portfolio import Portfolio


def display_portfolio_metrics(portfolio: Portfolio):
    """Display portfolio summary metrics in 3-column layout."""
    col1, col2, col3 = st.columns(3)

    # Total portfolio book value
    with col1:
        total_value = portfolio.total_value if hasattr(portfolio, 'total_value') else 0.0
        if total_value is None:
            total_value = sum(p.book_value for p in portfolio.positions)
        st.metric(
            "Total Book Value",
            f"${total_value:,.2f}" if total_value else "$0.00"
        )

    # Number of positions
    with col2:
        st.metric("Positions", len(portfolio.positions) if portfolio.positions else 0)

    # Largest position weight
    with col3:
        if portfolio.positions:
            weights = [p.weight for p in portfolio.positions if hasattr(p, 'weight') and p.weight]
            if weights:
                max_weight = max(weights)
                st.metric("Largest Position", f"{max_weight:.1f}%")
            else:
                st.metric("Largest Position", "N/A")
        else:
            st.metric("Largest Position", "N/A")
