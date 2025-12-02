"""Tabular view component with sector/country analysis."""

import streamlit as st
import pandas as pd
import plotly.express as px
from pagr.fds.models.portfolio import Portfolio
from pagr.fds.graph.queries import QueryService


def display_tabular_view(portfolio: Portfolio, query_service: QueryService):
    """Display tabular view with positions and exposure analysis."""
    st.subheader("Positions")

    positions_data = []
    for pos in portfolio.positions:
        book_value = pos.book_value if hasattr(pos, 'book_value') else 0.0
        market_value = pos.market_value if hasattr(pos, 'market_value') else None
        weight = pos.weight if hasattr(pos, 'weight') else 0.0
        security_type = pos.security_type if hasattr(pos, 'security_type') else "Unknown"

        positions_data.append({
            "Ticker": pos.ticker,
            "Quantity": pos.quantity,
            "Book Value": f"${book_value:,.2f}",
            "Market Value": f"${market_value:,.2f}" if market_value else "N/A",
            "Weight (%)": f"{weight:.2f}%" if weight else "N/A",
            "Type": security_type,
        })

    df_positions = pd.DataFrame(positions_data)
    st.dataframe(df_positions, use_container_width=True, hide_index=True)

    col1, col2 = st.columns([1, 1])

    # Sector Exposure
    with col1:
        st.subheader("Sector Exposure")
        try:
            sector_result = query_service.sector_exposure(portfolio.name)
            if sector_result and sector_result.records:
                sector_data = [dict(record) for record in sector_result.records]
                sector_df = pd.DataFrame(sector_data)

                # Display table
                st.dataframe(sector_df, use_container_width=True, hide_index=True)

                # Display chart
                if 'sector' in sector_df.columns and 'total_exposure' in sector_df.columns:
                    fig = px.bar(
                        sector_df,
                        x='sector',
                        y='total_exposure',
                        title='Exposure by Sector',
                        labels={'total_exposure': 'Exposure ($)', 'sector': 'Sector'}
                    )
                    fig.update_layout(
                        height=400,
                        xaxis={'categoryorder': 'total descending'},
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sector data. Portfolio may not be enriched with FactSet data yet.")
        except Exception as e:
            st.warning(f"Could not fetch sector exposure: {str(e)[:100]}")

    # Geographic Exposure
    with col2:
        st.subheader("Geographic Exposure")

        # Country selector with common options
        country_codes = ["US", "TW", "JP", "CN", "GB", "DE", "CA", "SG", "KR", "MX"]
        selected_country = st.selectbox("Select Country", country_codes, key="country_select")

        try:
            country_result = query_service.country_exposure(portfolio.name, selected_country)
            if country_result and country_result.records:
                country_data = [dict(record) for record in country_result.records]
                country_df = pd.DataFrame(country_data)

                # Display table
                st.dataframe(country_df, use_container_width=True, hide_index=True)

                # Display chart
                if 'company' in country_df.columns and 'exposure' in country_df.columns:
                    fig = px.bar(
                        country_df,
                        x='company',
                        y='exposure',
                        title=f'Exposure to {selected_country}',
                        labels={'exposure': 'Exposure ($)', 'company': 'Company'}
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No exposure to {selected_country} in current portfolio.")
        except Exception as e:
            st.warning(f"Could not fetch country exposure: {str(e)[:100]}")

    # Region Exposure
    st.subheader("Region Exposure")
    try:
        region_result = query_service.region_exposure(portfolio.name)
        if region_result and region_result.records:
            region_data = [dict(record) for record in region_result.records]
            region_df = pd.DataFrame(region_data)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(region_df, use_container_width=True, hide_index=True)
            with col2:
                if 'region' in region_df.columns and 'total_exposure' in region_df.columns:
                    fig = px.pie(
                        region_df,
                        names='region',
                        values='total_exposure',
                        title='Portfolio by Region'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No region data available.")
    except Exception as e:
        st.warning(f"Could not fetch region exposure: {str(e)[:100]}")
