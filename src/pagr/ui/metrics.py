"""Portfolio metrics display component."""

import streamlit as st
from typing import Union, List
from pagr.fds.models.portfolio import Portfolio


def display_portfolio_metrics(portfolios: Union[Portfolio, List[Portfolio]]):
    """Display portfolio summary metrics in 3-column layout.

    Supports both single and multiple portfolios. For multiple portfolios,
    displays aggregated metrics across all selected portfolios.

    Args:
        portfolios: Single Portfolio object or list of Portfolio objects
    """
    # Normalize to list for uniform handling
    if isinstance(portfolios, Portfolio):
        portfolios = [portfolios]

    col1, col2, col3 = st.columns(3)

    # Total portfolio value (aggregated across all portfolios)
    with col1:
        total_value = 0.0
        label = "Total Market Value"

        # Sum market values from all portfolios
        for portfolio in portfolios:
            pf_value = portfolio.total_value if hasattr(portfolio, 'total_value') else 0.0
            if pf_value:
                total_value += pf_value

        # If no market values, fall back to book values
        if not total_value:
            for portfolio in portfolios:
                if portfolio.positions:
                    total_value += sum(p.book_value for p in portfolio.positions)
            label = "Total Book Value"

        st.metric(
            label,
            f"${total_value:,.2f}" if total_value else "$0.00"
        )

    # Number of positions (total across all portfolios)
    with col2:
        total_positions = sum(
            len(portfolio.positions) if portfolio.positions else 0
            for portfolio in portfolios
        )
        st.metric("Positions", total_positions)

    # Largest position weight (max across all portfolios)
    with col3:
        all_weights = []
        for portfolio in portfolios:
            if portfolio.positions:
                weights = [p.weight for p in portfolio.positions if hasattr(p, 'weight') and p.weight]
                all_weights.extend(weights)

        if all_weights:
            max_weight = max(all_weights)
            st.metric("Largest Position", f"{max_weight:.1f}%")
        else:
            st.metric("Largest Position", "N/A")
