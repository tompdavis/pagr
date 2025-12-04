"""Settings tab UI component."""

import streamlit as st
import logging
from pathlib import Path
import yaml
from typing import Dict, Any, Optional

from pagr.session_manager import SessionManager
from pagr.connection_tester import test_all_connections

logger = logging.getLogger(__name__)


def load_config_yaml(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configuration dict or empty dict if file not found
    """
    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning(f"Config file not found: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def display_settings_tab(etl_manager):
    """Display settings tab with configuration and connection testing.

    Args:
        etl_manager: ETLManager instance for connection testing
    """
    st.header("⚙️ Settings")

    # Load config
    config = load_config_yaml()

    # Store config in session for potential future modifications
    if SessionManager.get_settings() is None:
        SessionManager.set_settings(config)

    # Auto-test connections on first load
    if not SessionManager.connections_already_tested():
        with st.spinner("Testing connections..."):
            try:
                test_results = test_all_connections(etl_manager)
                for service, result in test_results.items():
                    SessionManager.set_connection_status(
                        service,
                        result["status"],
                        result["message"]
                    )
                SessionManager.mark_connections_tested()
                st.rerun()
            except Exception as e:
                st.error(f"Error during connection test: {e}")
                logger.exception("Connection test failed")

    # Display connection status summary
    st.subheader("Connection Status")

    col1, col2, col3 = st.columns(3)

    connection_statuses = SessionManager.get_all_connection_status()

    with col1:
        memgraph_status = connection_statuses.get("memgraph", {})
        status_icon = "✅" if memgraph_status.get("status") == "success" else "❌"
        st.metric("Memgraph", status_icon, "Connected" if status_icon == "✅" else "Disconnected")

    with col2:
        factset_status = connection_statuses.get("factset", {})
        status_icon = "✅" if factset_status.get("status") == "success" else "❌"
        st.metric("FactSet", status_icon, "Connected" if status_icon == "✅" else "Disconnected")

    with col3:
        llm_status = connection_statuses.get("llm", {})
        status_icon = "⚠️"  # Always warning for not implemented
        st.metric("LLM", status_icon, "Not Implemented")

    st.divider()

    # Memgraph Settings
    st.subheader("Memgraph Database")

    col1, col2 = st.columns([1, 1])

    with col1:
        memgraph_config = config.get("memgraph", {})
        st.text_input(
            "Host",
            value=memgraph_config.get("host", "127.0.0.1"),
            disabled=True,
            key="memgraph_host"
        )
        st.number_input(
            "Port",
            value=memgraph_config.get("port", 7687),
            disabled=True,
            key="memgraph_port"
        )

    with col2:
        st.text_input(
            "Username",
            value=memgraph_config.get("username", ""),
            disabled=True,
            key="memgraph_username"
        )
        st.text_input(
            "Password",
            value="***" if memgraph_config.get("password") else "",
            disabled=True,
            key="memgraph_password",
            type="password"
        )

    # Memgraph test button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Test Memgraph", key="test_memgraph_btn", use_container_width=True):
            with st.spinner("Testing Memgraph connection..."):
                try:
                    from pagr.connection_tester import test_memgraph_connection
                    success, message = test_memgraph_connection(etl_manager.memgraph_client)
                    SessionManager.set_connection_status(
                        "memgraph",
                        "success" if success else "error",
                        message
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                except Exception as e:
                    error_msg = f"❌ Test Failed: {str(e)}"
                    SessionManager.set_connection_status("memgraph", "error", error_msg)
                    st.error(error_msg)

    # Show detailed memgraph error if any
    memgraph_status = connection_statuses.get("memgraph", {})
    if memgraph_status.get("status") == "error" and memgraph_status.get("message"):
        with st.expander("Memgraph Error Details"):
            st.error(memgraph_status.get("message"))

    st.divider()

    # FactSet Settings
    st.subheader("FactSet API")

    col1, col2 = st.columns([1, 1])

    with col1:
        factset_config = config.get("factset", {})
        st.text_input(
            "Username",
            value=factset_config.get("username", ""),
            disabled=True,
            key="factset_username"
        )
        st.text_input(
            "Base URL",
            value=factset_config.get("base_url", "https://api.factset.com"),
            disabled=True,
            key="factset_base_url"
        )

    with col2:
        st.text_input(
            "API Key",
            value="***" if factset_config.get("api_key") else "",
            disabled=True,
            key="factset_api_key",
            type="password"
        )
        st.number_input(
            "Rate Limit (RPS)",
            value=factset_config.get("rate_limit_rps", 10),
            disabled=True,
            key="factset_rate_limit"
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.number_input(
            "Timeout (seconds)",
            value=factset_config.get("timeout", 30),
            disabled=True,
            key="factset_timeout"
        )

    with col2:
        st.number_input(
            "Max Retries",
            value=factset_config.get("max_retries", 3),
            disabled=True,
            key="factset_max_retries"
        )

    # FactSet test button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Test FactSet", key="test_factset_btn", use_container_width=True):
            with st.spinner("Testing FactSet connection (fetching FDS price)..."):
                try:
                    from pagr.connection_tester import test_factset_connection
                    success, message = test_factset_connection(etl_manager.factset_client)
                    SessionManager.set_connection_status(
                        "factset",
                        "success" if success else "error",
                        message
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                except Exception as e:
                    error_msg = f"❌ Test Failed: {str(e)}"
                    SessionManager.set_connection_status("factset", "error", error_msg)
                    st.error(error_msg)

    # Show detailed factset error if any
    factset_status = connection_statuses.get("factset", {})
    if factset_status.get("status") == "error" and factset_status.get("message"):
        with st.expander("FactSet Error Details"):
            st.error(factset_status.get("message"))

    st.divider()

    # Logging Settings
    st.subheader("Logging")

    logging_config = config.get("logging", {})

    col1, col2 = st.columns([1, 1])

    with col1:
        st.selectbox(
            "Log Level",
            options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(
                logging_config.get("level", "INFO")
            ),
            disabled=True,
            key="logging_level"
        )

    with col2:
        st.text_input(
            "Log File Path",
            value=logging_config.get("file", "logs/pagr.log"),
            disabled=True,
            key="logging_file"
        )

    st.divider()

    # LLM Settings (Placeholder)
    st.subheader("LLM Configuration (Future Feature)")

    st.info("🚧 LLM integration is planned for a future release.")
    st.info("⚠️ For now, LLM functionality is not implemented.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.text_input(
            "LLM Provider URL",
            value="https://ollama.com/api/generate",
            disabled=True,
            placeholder="LLM provider endpoint"
        )
        st.text_input(
            "Chat Agent Model",
            value="gpt-oss:20b-cloud",
            disabled=True,
            placeholder="Model for portfolio chat"
        )

    with col2:
        st.text_input(
            "API Key",
            value="",
            disabled=True,
            type="password",
            placeholder="LLM API key"
        )
        st.text_input(
            "Cypher Model",
            value="qwen3-coder:480b-cloud",
            disabled=True,
            placeholder="Model for Cypher generation"
        )

    if st.button("Test LLM", key="test_llm_btn", use_container_width=False, disabled=True):
        st.info("LLM testing will be available in a future release.")

    st.divider()

    # Settings Info
    st.info(
        "💡 **Note**: Settings are displayed from `config/config.yaml`. "
        "To modify settings, please edit the configuration file directly. "
        "Settings persistence will be added in a future release."
    )
