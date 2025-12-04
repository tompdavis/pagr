"""PAGR - Portfolio Analysis with Graph Relationships and FactSet Enrichment."""

import streamlit as st
import logging

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

# Initialize portfolio manager
@st.cache_resource
def get_portfolio_manager():
    """Create and cache portfolio manager instance."""
    return PortfolioManager(etl_manager.memgraph_client)

portfolio_manager = get_portfolio_manager()

# Page title
st.title("📊 PAGR - Portfolio Analysis with Graph Relationships")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "⚙️ Settings",
    "📁 Portfolio Selection",
    "📊 Holdings View",
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

# Portfolio Chat Agent Tab
with tab4:
    from pagr.ui.tab_chat_agent import display_chat_agent_tab
    display_chat_agent_tab()

# Footer
st.divider()
st.caption("PAGR v0.2.0 | FactSet + FIBO Integration | Multi-Portfolio Support (Beta)")
