"""Tabular view component with sector/country analysis."""

import logging
import streamlit as st
import pandas as pd
import plotly.express as px
from pagr.fds.models.portfolio import Portfolio
from pagr.fds.graph.queries import QueryService
from pagr.errors import UIRenderError

logger = logging.getLogger(__name__)


def _pad_dataframe_to_height(df, max_rows=10):
    """Pad dataframe with empty rows to ensure uniform table height."""
    df_copy = df.copy()
    while len(df_copy) < max_rows:
        df_copy = pd.concat([df_copy, pd.DataFrame([{col: "" for col in df_copy.columns}])], ignore_index=True)
    return df_copy


def _get_security_description(position):
    """Generate security description for display (ticker for stocks, CUSIP/ISIN for bonds).

    Args:
        position: Position object

    Returns:
        String describing the security (ticker for stocks, CUSIP (Bond) or ISIN (Bond) for bonds)
    """
    if position.ticker:
        return position.ticker
    elif position.cusip:
        return f"{position.cusip} (Bond)"
    elif position.isin:
        return f"{position.isin} (Bond)"
    else:
        return "Unknown"


def display_tabular_view(portfolios, query_service: QueryService):
    """Display tabular view with positions and exposure analysis.

    Args:
        portfolios: Single Portfolio object or list of Portfolio objects
        query_service: QueryService instance for executing graph queries
    """
    # Normalize to list for uniform handling
    if isinstance(portfolios, Portfolio):
        portfolios = [portfolios]

    st.subheader("Positions")

    try:
        positions_data = []
        for portfolio in portfolios:
            for pos in portfolio.positions:
                try:
                    book_value = pos.book_value if hasattr(pos, 'book_value') else 0.0
                    market_value = pos.market_value if hasattr(pos, 'market_value') else None
                    weight = pos.weight if hasattr(pos, 'weight') else 0.0
                    security_type = pos.security_type if hasattr(pos, 'security_type') else "Unknown"
                    security_desc = _get_security_description(pos)

                    positions_data.append({
                        "Portfolio": portfolio.name,
                        "Security": security_desc,
                        "Type": security_type,
                        "Quantity": pos.quantity,
                        "Book Value": f"${book_value:,.2f}",
                        "Market Value (Last Close)": f"${market_value:,.2f}" if market_value else "N/A",
                        "Weight (%)": f"{weight:.2f}%" if weight else "N/A",
                    })
                except Exception as e:
                    logger.error(f"Error processing position: {e}")
                    st.warning(f"⚠️ Could not display one position: {str(e)[:100]}")
                    continue

        if positions_data:
            df_positions = pd.DataFrame(positions_data)
            st.dataframe(df_positions, width='stretch', hide_index=True)
        else:
            st.info("No positions to display")
    except Exception as e:
        error = UIRenderError(str(e), component="Positions Table")
        error.log_error()
        st.error(f"❌ Error displaying positions: {error.message}")

    col1, col2 = st.columns([1, 1])

    # Extract portfolio names for queries
    portfolio_names = [p.name for p in portfolios]

    # Sector Exposure (Left Column)
    with col1:
        st.subheader("Sector Exposure")
        try:
            # Get sector breakdown
            try:
                sector_result = query_service.sector_exposure(portfolio_names)
            except Exception as e:
                logger.error(f"Error querying sector exposure: {e}")
                raise UIRenderError(f"Failed to query sector exposure: {str(e)[:100]}", component="Sector Exposure")

            if sector_result and sector_result.records:
                try:
                    sector_data = [dict(record) for record in sector_result.records]
                    sector_df = pd.DataFrame(sector_data)

                    # Display sector breakdown table
                    display_df = sector_df.copy()
                    if 'total_exposure' in display_df.columns:
                        display_df['total_exposure'] = display_df['total_exposure'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
                    if 'total_weight' in display_df.columns:
                        display_df['total_weight'] = display_df['total_weight'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%")

                    if 'num_positions' in display_df.columns:
                        display_df = display_df.drop(columns=['num_positions'])

                    display_df = display_df.rename(columns={
                        'sector': 'Sector',
                        'total_exposure': 'Exposure',
                        'total_weight': 'Weight'
                    })

                    st.write("**Sector Breakdown**")
                    display_df = _pad_dataframe_to_height(display_df, max_rows=10)
                    st.dataframe(display_df, width='stretch', hide_index=True)
                except Exception as e:
                    logger.error(f"Error formatting sector data: {e}")
                    st.warning(f"⚠️ Error formatting sector data: {str(e)[:100]}")

                # Display sector breakdown chart
                if 'sector' in sector_df.columns and 'total_exposure' in sector_df.columns:
                    fig = px.bar(
                        sector_df,
                        x='sector',
                        y='total_exposure',
                        title='Exposure by Sector',
                        labels={'total_exposure': 'Market Exposure ($)', 'sector': 'Sector'}
                    )
                    fig.update_layout(
                        height=400,
                        xaxis={'categoryorder': 'total descending'},
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Sector selector
                sectors = sorted(sector_df['sector'].dropna().unique().tolist())
                selected_sector = st.selectbox(
                    "Select Sector to View Positions",
                    sectors,
                    key="sector_select"
                )

                # Get positions in selected sector
                if selected_sector:
                    sector_pos_result = query_service.sector_positions(portfolio_names, selected_sector)
                    if sector_pos_result and sector_pos_result.records:
                        sector_pos_data = [dict(record) for record in sector_pos_result.records]
                        sector_pos_df = pd.DataFrame(sector_pos_data)

                        # Format columns for display
                        display_sector_pos_df = sector_pos_df.copy()
                        if 'market_value' in display_sector_pos_df.columns:
                            display_sector_pos_df['market_value'] = display_sector_pos_df['market_value'].apply(
                                lambda x: f"${x:,.2f}" if pd.notnull(x) and x != 0 else ("N/A" if pd.isnull(x) else "$0.00")
                            )
                        if 'weight' in display_sector_pos_df.columns:
                            display_sector_pos_df['weight'] = display_sector_pos_df['weight'].apply(
                                lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"
                            )

                        display_sector_pos_df = display_sector_pos_df.rename(columns={
                            'portfolio_name': 'Portfolio',
                            'ticker': 'Security',
                            'company': 'Company',
                            'quantity': 'Quantity',
                            'market_value': 'Market Value',
                            'weight': 'Weight'
                        })
                        # For bonds (ticker is NULL), display company name or N/A
                        if 'Security' in display_sector_pos_df.columns:
                            display_sector_pos_df['Security'] = display_sector_pos_df.apply(
                                lambda row: row['Security'] if pd.notnull(row['Security']) and row['Security'] != '' else 'Bond',
                                axis=1
                            )

                        st.write(f"**Positions in {selected_sector}**")
                        st.dataframe(display_sector_pos_df, width='stretch', hide_index=True)

                        # Display chart of positions in selected sector
                        if 'company' in sector_pos_df.columns and 'market_value' in sector_pos_df.columns:
                            fig = px.bar(
                                sector_pos_df,
                                x='company',
                                y='market_value',
                                title=f'Positions in {selected_sector}',
                                labels={'market_value': 'Market Value ($)', 'company': 'Company'}
                            )
                            fig.update_layout(height=400, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No positions found in {selected_sector} sector.")
            else:
                st.info("No sector data. Portfolio may not be enriched with FactSet data yet.")
        except Exception as e:
            st.warning(f"Could not fetch sector data: {str(e)[:100]}")

    # Geographic Exposure (Right Column)
    with col2:
        st.subheader("Geographic Exposure")
        try:
            # Get country breakdown
            country_result = query_service.country_breakdown(portfolio_names)
            if country_result and country_result.records:
                country_data = [dict(record) for record in country_result.records]
                country_df = pd.DataFrame(country_data)

                # Display country breakdown table
                display_country_df = country_df.copy()
                if 'total_exposure' in display_country_df.columns:
                    display_country_df['total_exposure'] = display_country_df['total_exposure'].apply(
                        lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                    )
                if 'total_weight' in display_country_df.columns:
                    display_country_df['total_weight'] = display_country_df['total_weight'].apply(
                        lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"
                    )

                if 'num_positions' in display_country_df.columns:
                    display_country_df = display_country_df.drop(columns=['num_positions'])
                if 'country' in display_country_df.columns:
                    display_country_df = display_country_df.drop(columns=['country'])

                display_country_df = display_country_df.rename(columns={
                    'country_code': 'Country',
                    'total_exposure': 'Exposure',
                    'total_weight': 'Weight'
                })

                st.write("**Country Breakdown**")
                display_country_df = _pad_dataframe_to_height(display_country_df, max_rows=10)
                st.dataframe(display_country_df, width='stretch', hide_index=True)

                # Display country breakdown chart
                if 'country_code' in country_df.columns and 'total_exposure' in country_df.columns:
                    fig = px.bar(
                        country_df,
                        x='country_code',
                        y='total_exposure',
                        title='Exposure by Country',
                        labels={'total_exposure': 'Market Exposure ($)', 'country_code': 'Country'}
                    )
                    fig.update_layout(
                        height=400,
                        xaxis={'categoryorder': 'total descending'},
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Country selector
                country_codes = sorted(country_df['country_code'].dropna().unique().tolist())
                selected_country = st.selectbox(
                    "Select Country to View Positions",
                    country_codes,
                    key="country_select"
                )

                # Get positions in selected country
                if selected_country:
                    country_pos_result = query_service.country_positions(portfolio_names, selected_country)
                    if country_pos_result and country_pos_result.records:
                        country_pos_data = [dict(record) for record in country_pos_result.records]
                        country_pos_df = pd.DataFrame(country_pos_data)

                        # Format columns for display
                        display_country_pos_df = country_pos_df.copy()
                        if 'market_value' in display_country_pos_df.columns:
                            display_country_pos_df['market_value'] = display_country_pos_df['market_value'].apply(
                                lambda x: f"${x:,.2f}" if pd.notnull(x) and x != 0 else ("N/A" if pd.isnull(x) else "$0.00")
                            )
                        if 'weight' in display_country_pos_df.columns:
                            display_country_pos_df['weight'] = display_country_pos_df['weight'].apply(
                                lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"
                            )

                        display_country_pos_df = display_country_pos_df.rename(columns={
                            'portfolio_name': 'Portfolio',
                            'ticker': 'Security',
                            'company': 'Company',
                            'quantity': 'Quantity',
                            'market_value': 'Market Value',
                            'weight': 'Weight'
                        })
                        # For bonds (ticker is NULL), display company name or N/A
                        if 'Security' in display_country_pos_df.columns:
                            display_country_pos_df['Security'] = display_country_pos_df.apply(
                                lambda row: row['Security'] if pd.notnull(row['Security']) and row['Security'] != '' else 'Bond',
                                axis=1
                            )

                        st.write(f"**Positions in {selected_country}**")
                        st.dataframe(display_country_pos_df, width='stretch', hide_index=True)

                        # Display chart of positions in selected country
                        if 'company' in country_pos_df.columns and 'market_value' in country_pos_df.columns:
                            fig = px.bar(
                                country_pos_df,
                                x='company',
                                y='market_value',
                                title=f'Positions in {selected_country}',
                                labels={'market_value': 'Market Value ($)', 'company': 'Company'}
                            )
                            fig.update_layout(height=400, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No positions found in {selected_country}.")
            else:
                st.info("No geographic data. Portfolio may not be enriched with FactSet data yet.")
        except Exception as e:
            st.warning(f"Could not fetch geographic data: {str(e)[:100]}")


