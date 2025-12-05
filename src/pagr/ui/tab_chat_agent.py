"""Portfolio Chat Agent tab UI component."""

import streamlit as st
import logging
import pandas as pd
import plotly.express as px

from pagr.session_manager import SessionManager
from pagr.portfolio_loader import PortfolioLoader
from pagr.portfolio_analysis_service import PortfolioAnalysisService
from pagr.portfolio_manager import PortfolioManager
from pagr.ui.components import display_portfolio_selector

logger = logging.getLogger(__name__)


def display_chat_agent_tab(portfolio_manager: PortfolioManager, query_service):
    """Display chat agent tab with portfolio selector and query interface.

    Args:
        portfolio_manager: PortfolioManager instance
        query_service: QueryService instance for executing graph queries
    """
    st.info("💬 Portfolio Query Interface\n\nSelect portfolios and run predefined queries. LLM-powered natural language queries coming soon.")

    # Initialize services
    portfolio_loader = PortfolioLoader(portfolio_manager)

    # Get and display available portfolios
    try:
        available_portfolios = portfolio_loader.get_available_portfolios(force_refresh=False)

        if not available_portfolios:
            st.warning("📌 No portfolios found. Please upload a portfolio in Portfolio Selection tab.")
            return

    except Exception as e:
        logger.error(f"Error loading portfolios: {e}")
        st.error("❌ Could not load portfolios from database")
        return

    # Initialize analysis service
    analysis_service = PortfolioAnalysisService(query_service) if query_service else None

    # Two-column layout: Portfolio selector (left) + Query interface (right)
    selected_portfolios = display_portfolio_selector(
        available_portfolios,
        column_width=(1, 2),
        key_prefix="chat_portfolio_selector",
    )

    left_col, right_col = st.columns([1, 2])

    with right_col:
        st.subheader("Query Builder")

        # Get selected portfolios
        selected_portfolios = SessionManager.get_selected_portfolios()

        if not selected_portfolios:
            st.info("Please select at least one portfolio to run queries.")
            return

        # Query type selector
        query_type = st.selectbox(
            "Select Query Type",
            [
                "Sector Exposure",
                "Country Exposure",
                "Country Positions",
                "Sector Positions",
                "Executive Lookup"
            ],
            help="Choose the type of portfolio analysis to run"
        )

        st.divider()

        # Run query based on selected type
        if query_type == "Sector Exposure":
            _display_sector_exposure(query_service, selected_portfolios)

        elif query_type == "Country Exposure":
            _display_country_exposure(query_service, selected_portfolios)

        elif query_type == "Country Positions":
            _display_country_positions(query_service, selected_portfolios)

        elif query_type == "Sector Positions":
            _display_sector_positions(query_service, selected_portfolios)

        elif query_type == "Executive Lookup":
            _display_executive_lookup(query_service, selected_portfolios)


def _display_sector_exposure(query_service, portfolio_names):
    """Display sector exposure query results."""
    try:
        result = query_service.sector_exposure(portfolio_names)
        if result and result.records:
            df = pd.DataFrame([dict(r) for r in result.records])

            # Format for display
            display_df = df.copy()
            if 'total_exposure' in display_df.columns:
                display_df['total_exposure'] = display_df['total_exposure'].apply(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )
            if 'total_weight' in display_df.columns:
                display_df['total_weight'] = display_df['total_weight'].apply(
                    lambda x: f"{x:.2f}%" if pd.notnull(x) else "0%"
                )

            st.write("**Sector Breakdown**")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Chart
            if 'sector' in df.columns and 'total_exposure' in df.columns:
                fig = px.bar(
                    df,
                    x='sector',
                    y='total_exposure',
                    title='Exposure by Sector',
                    labels={'total_exposure': 'Market Exposure ($)', 'sector': 'Sector'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector data available")
    except Exception as e:
        st.error(f"Error running sector exposure query: {str(e)}")
        logger.exception(f"Sector exposure error: {e}")


def _display_country_exposure(query_service, portfolio_names):
    """Display country exposure query results."""
    try:
        # Get list of countries first
        country_breakdown = query_service.country_breakdown(portfolio_names)
        if country_breakdown and country_breakdown.records:
            countries = [r.get('country_code') for r in country_breakdown.records if r.get('country_code')]

            if not countries:
                st.info("No country data available")
                return

            selected_country = st.selectbox("Select Country", countries, key="chat_country_select")

            if selected_country:
                result = query_service.country_exposure(portfolio_names, selected_country)
                if result and result.records:
                    df = pd.DataFrame([dict(r) for r in result.records])

                    # Format for display
                    display_df = df.copy()
                    if 'exposure' in display_df.columns:
                        display_df['exposure'] = display_df['exposure'].apply(
                            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                        )

                    st.write(f"**Exposure in {selected_country}**")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No exposure data for {selected_country}")
        else:
            st.info("No country data available")
    except Exception as e:
        st.error(f"Error running country exposure query: {str(e)}")
        logger.exception(f"Country exposure error: {e}")


def _display_country_positions(query_service, portfolio_names):
    """Display country positions query results."""
    try:
        # Get list of countries first
        country_breakdown = query_service.country_breakdown(portfolio_names)
        if country_breakdown and country_breakdown.records:
            countries = [r.get('country_code') for r in country_breakdown.records if r.get('country_code')]

            if not countries:
                st.info("No country data available")
                return

            selected_country = st.selectbox("Select Country", countries, key="chat_country_positions_select")

            if selected_country:
                result = query_service.country_positions(portfolio_names, selected_country)
                if result and result.records:
                    df = pd.DataFrame([dict(r) for r in result.records])

                    # Format for display
                    display_df = df.copy()
                    if 'market_value' in display_df.columns:
                        display_df['market_value'] = display_df['market_value'].apply(
                            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                        )
                    if 'weight' in display_df.columns:
                        display_df['weight'] = display_df['weight'].apply(
                            lambda x: f"{x:.2f}%" if pd.notnull(x) else "0%"
                        )

                    st.write(f"**Positions in {selected_country}**")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No positions in {selected_country}")
        else:
            st.info("No country data available")
    except Exception as e:
        st.error(f"Error running country positions query: {str(e)}")
        logger.exception(f"Country positions error: {e}")


def _display_sector_positions(query_service, portfolio_names):
    """Display sector positions query results."""
    try:
        # Get list of sectors first
        sector_exposure = query_service.sector_exposure(portfolio_names)
        if sector_exposure and sector_exposure.records:
            sectors = [r.get('sector') for r in sector_exposure.records if r.get('sector')]

            if not sectors:
                st.info("No sector data available")
                return

            selected_sector = st.selectbox("Select Sector", sectors, key="chat_sector_select")

            if selected_sector:
                result = query_service.sector_positions(portfolio_names, selected_sector)
                if result and result.records:
                    df = pd.DataFrame([dict(r) for r in result.records])

                    # Format for display
                    display_df = df.copy()
                    if 'market_value' in display_df.columns:
                        display_df['market_value'] = display_df['market_value'].apply(
                            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                        )
                    if 'weight' in display_df.columns:
                        display_df['weight'] = display_df['weight'].apply(
                            lambda x: f"{x:.2f}%" if pd.notnull(x) else "0%"
                        )

                    st.write(f"**Positions in {selected_sector}**")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No positions in {selected_sector}")
        else:
            st.info("No sector data available")
    except Exception as e:
        st.error(f"Error running sector positions query: {str(e)}")
        logger.exception(f"Sector positions error: {e}")


def _display_executive_lookup(query_service, portfolio_names):
    """Display executive lookup query results."""
    try:
        result = query_service.executive_lookup(portfolio_names)
        if result and result.records:
            df = pd.DataFrame([dict(r) for r in result.records])

            # Format for display
            display_df = df.copy()
            if 'position_value' in display_df.columns:
                display_df['position_value'] = display_df['position_value'].apply(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )

            st.write("**Portfolio Company Executives**")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No executive data available")
    except Exception as e:
        st.error(f"Error running executive lookup query: {str(e)}")
        logger.exception(f"Executive lookup error: {e}")
