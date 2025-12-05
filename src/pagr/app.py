"""PAGR - Portfolio Analysis with Graph Relationships and FactSet Enrichment."""

import streamlit as st
import logging
import base64
from pathlib import Path

from pagr.session_manager import SessionManager
from pagr.etl_manager import ETLManager
from pagr.portfolio_manager import PortfolioManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="PAGR - Portfolio Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS styling for fixed header and tabs
st.markdown(
    """
    <style>
    html, body {
        margin: 0;
        padding: 0;
    }
    /* Streamlit toolbar positioning */
    header[data-testid="stHeader"] {
        z-index: 10;
    }
    .main {
        background-color: #f0f2f6;
        margin-top: 360px !important;
        padding-top: 0 !important;
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
    /* Fixed header - positioned below Streamlit toolbar */
    #pagr-fixed-header {
        position: fixed;
        top: 60px;
        left: 0;
        right: 0;
        z-index: 998;
        background-color: white;
        padding: 1.5rem 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 2rem;
        height: 160px;
        box-sizing: border-box;
        overflow: hidden;
    }
    #pagr-header-image {
        flex-shrink: 0;
        height: 120px;
        object-fit: contain;
    }
    #pagr-header-title {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin: 0;
        padding: 0;
        white-space: nowrap;
    }
    /* Fixed tabs - positioned below header */
    [role="tablist"] {
        position: fixed !important;
        top: 230px !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 997 !important;
        background-color: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        padding: 0 2rem !important;
        margin: 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
        display: flex !important;
        border-bottom: 1px solid #e0e0e0;
    }
    /* Tab item styling */
    [role="tab"] {
        background-color: transparent;
        border: none;
        padding: 1rem 0.75rem;
        margin-right: 0.5rem;
        color: #666;
        cursor: pointer;
        font-size: 1.1rem;
        font-weight: 500;
    }
    [role="tab"][aria-selected="true"] {
        background-color: transparent;
        color: #1f77b4;
        box-shadow: inset 0 -3px 0 #1f77b4;
    }
    /* Add space for tabs below header */
    [role="tabpanel"] {
        margin-top: 80px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load and encode image as base64
image_path = Path("marketing/graph_asset_2.png")
if image_path.exists():
    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()

    # Create fixed header with pure HTML
    st.markdown(
        f"""
        <div id="pagr-fixed-header">
            <img id="pagr-header-image" src="data:image/png;base64,{img_base64}" width="300" />
            <h1 id="pagr-header-title">Graph RAG Across Portfolio Holdings</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.error(f"Image not found at {image_path}")

# Initialize session state
SessionManager.initialize()

# Initialize ETL manager (cached)
@st.cache_resource
def get_etl_manager():
    """Create and cache ETL manager instance."""
    return ETLManager(config_path="config/config.yaml")

etl_manager = get_etl_manager()

# Initialize portfolio manager
@st.cache_resource
def get_portfolio_manager():
    """Create and cache portfolio manager instance."""
    return PortfolioManager(etl_manager.memgraph_client)

portfolio_manager = get_portfolio_manager()

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚙️ Settings",
    "📁 Portfolio Selection",
    "📊 Holdings View",
    "🔗 Graph View",
    "💬 Portfolio Chat Agent"
])

# Settings Tab
with tab1:
    from pagr.ui.tab_settings import display_settings_tab
    display_settings_tab(etl_manager)

# Portfolio Selection Tab
with tab2:
    from pagr.ui.tab_portfolio_selection import display_portfolio_selection_tab
    display_portfolio_selection_tab(etl_manager, portfolio_manager)

# Holdings View Tab
with tab3:
    from pagr.ui.tab_holdings import display_holdings_tab
    display_holdings_tab(etl_manager, portfolio_manager)

# Graph View Tab
with tab4:
    from pagr.ui.tab_graph_view import display_graph_view_tab
    display_graph_view_tab(etl_manager, portfolio_manager)

# Portfolio Chat Agent Tab
with tab5:
    from pagr.ui.tab_chat_agent import display_chat_agent_tab
    display_chat_agent_tab(portfolio_manager, etl_manager.query_service)

# Footer
st.divider()
st.caption("PAGR v0.2.0 | FactSet + FIBO Integration | Multi-Portfolio Support (Beta)")
