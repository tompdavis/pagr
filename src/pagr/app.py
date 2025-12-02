"""PAGR - Portfolio Analysis with Graph Relationships and FactSet Enrichment."""

import streamlit as st
from pathlib import Path
import logging

from pagr.session_manager import SessionManager
from pagr.etl_manager import ETLManager
from pagr.ui.metrics import display_portfolio_metrics
from pagr.ui.tabular import display_tabular_view
from pagr.ui.graph_view import display_graph_view

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="PAGR - Portfolio Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown(
    """
    <style>
    .main {
        background-color: #f0f2f6;
    }
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
    h1 {
        color: #1f77b4;
    }
    h2 {
        color: #ff7f0e;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize session state
SessionManager.initialize()

# Initialize ETL manager (cached)
@st.cache_resource
def get_etl_manager():
    """Create and cache ETL manager instance."""
    return ETLManager(config_path="config/config.yaml")

etl_manager = get_etl_manager()

# Sidebar
with st.sidebar:
    # Logo if it exists
    logo_path = Path("marketing/pagr_asset_1.png")
    if logo_path.exists():
        st.image(str(logo_path), width=200)

    st.divider()

    st.header("Portfolio Management")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Portfolio CSV",
        type="csv",
        help="CSV format: ticker,quantity,book_value,security_type (optional),isin (optional),cusip (optional). "
             "book_value = cost basis (what you paid), market_value is optional and can be fetched separately."
    )

    # Process uploaded file
    if uploaded_file is not None:
        current_file = SessionManager.get_current_file()

        if current_file != uploaded_file.name:
            SessionManager.set_current_file(uploaded_file.name)

            with st.spinner("Processing portfolio through ETL pipeline..."):
                try:
                    # Check Memgraph connection first
                    if not etl_manager.check_connection():
                        st.error(
                            "Cannot connect to Memgraph database. "
                            "Please ensure Memgraph is running on 127.0.0.1:7687"
                        )
                    else:
                        # Process CSV
                        portfolio, stats = etl_manager.process_uploaded_csv(uploaded_file)
                        SessionManager.set_portfolio(portfolio, stats)
                        SessionManager.set_query_service(etl_manager.query_service)

                        st.success(f"Portfolio '{portfolio.name}' loaded successfully!")

                        # Show pipeline statistics
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

                except Exception as e:
                    st.error(f"Error processing portfolio: {str(e)}")
                    logger.exception(f"Portfolio processing error: {e}")

    st.divider()

    # View selection
    st.subheader("Display Options")
    view_selection = st.radio(
        "Select View",
        ["Tabular Analysis", "Graph Visualization"],
        horizontal=False
    )

    st.divider()

    # Database management
    with st.expander("Database Management"):
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear Database", use_container_width=True):
                try:
                    etl_manager.clear_database()
                    SessionManager.clear()
                    st.success("Database cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear: {e}")
                    logger.error(f"Clear database error: {e}")

        with col2:
            if st.button("Database Stats", use_container_width=True):
                try:
                    stats = etl_manager.get_database_stats()
                    if stats:
                        st.json(stats)
                    else:
                        st.info("No database stats available")
                except Exception as e:
                    st.warning(f"Error getting stats: {e}")

    st.divider()
    st.caption("PAGR v0.1.0 | FactSet + FIBO Integration")

# Main content
portfolio = SessionManager.get_portfolio()

if portfolio is None:
    # Welcome screen
    st.title("Welcome to PAGR")
    st.markdown("""
        ### Portfolio Analysis with Graph Relationships

        **PAGR** combines:
        - 📈 **Portfolio Management** with CSV-based loading
        - 🌐 **FactSet Data Enrichment** for company insights
        - 📊 **FIBO Ontology** graph relationships
        - 🎯 **Sector & Geographic Analysis**
        - 🔗 **Interactive Graph Visualization**

        ---

        ### Getting Started

        1. **Prepare CSV File** with portfolio data:
           ```csv
           ticker,quantity,book_value,security_type,isin,cusip
           AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
           MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
           ```

           Where `book_value` is the cost basis (what you paid), and optional `market_value` can be added for current prices.

        2. **Upload CSV** via sidebar file uploader

        3. **Wait for Enrichment** - PAGR will:
           - Load positions from CSV
           - Fetch company data from FactSet API
           - Enrich with geographic information
           - Build FIBO graph in Memgraph
           - Create analysis queries

        4. **Explore Data**:
           - **Tabular View**: Sector/country exposure, charts
           - **Graph View**: FIBO relationships, companies, executives

        ---

        ### Features

        #### Tabular Analysis
        - Portfolio position listing with market values
        - Sector exposure breakdown
        - Geographic exposure by country
        - Regional distribution charts

        #### Graph Visualization
        - Interactive FIBO graph
        - Toggle: Executives, Countries, Subsidiaries
        - Color-coded nodes by entity type
        - Relationship labels

        #### FIBO Schema
        - **Nodes**: Portfolio, Position, Company, Country, Executive
        - **Relationships**: CONTAINS, ISSUED_BY, HEADQUARTERED_IN, CEO_OF

        ---

        ### Requirements

        - **Memgraph**: Running on localhost:7687
        - **FactSet API**: Credentials in `fds-api.key`
        - **Portfolio CSV**: With ticker, quantity, market_value columns

        ---

        ### Support

        Upload a CSV file to begin!
    """)

else:
    # Display loaded portfolio
    st.header(f"Portfolio: {portfolio.name}")

    # Display metrics
    display_portfolio_metrics(portfolio)
    st.divider()

    # Display selected view
    query_service = SessionManager.get_query_service()

    if view_selection == "Tabular Analysis":
        if query_service:
            display_tabular_view(portfolio, query_service)
        else:
            st.error("Query service not initialized")

    elif view_selection == "Graph Visualization":
        display_graph_view(portfolio, etl_manager.memgraph_client)
