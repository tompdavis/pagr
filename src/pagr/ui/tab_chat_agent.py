"""Portfolio Chat Agent tab UI component (placeholder)."""

import streamlit as st


def display_chat_agent_tab():
    """Display placeholder for portfolio chat agent tab.

    This is a placeholder for future LLM-powered portfolio analysis functionality.
    """
    st.header("💬 Portfolio Chat Agent")

    st.info("🚧 This feature is under development and will be available in a future release.")

    # Create layout: Left half for chat, right half split for graph and table
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Chat Window")
        st.info("NOT IMPLEMENTED YET\n\nThis section will contain a chat interface for querying your portfolio with natural language questions.")

    with right_col:
        top_col, bottom_col = st.columns([1, 1])

        with top_col:
            st.subheader("Graph View")
            st.info("NOT IMPLEMENTED YET\n\nThis section will display graph visualizations resulting from chat queries.")

        with bottom_col:
            st.subheader("Tabular View")
            st.info("NOT IMPLEMENTED YET\n\nThis section will display tabular data resulting from chat queries.")

    st.divider()

    st.markdown("""
    ### Planned Features
    - Natural language querying of portfolio data
    - LLM-powered analysis of portfolio exposures
    - Interactive graph and table visualizations
    - Scenario analysis through conversation
    - Portfolio insights and recommendations

    ### Development Status
    - [ ] LLM provider integration (Ollama/OpenAI)
    - [ ] Natural language to Cypher translation
    - [ ] Chat history management
    - [ ] Query result visualization
    - [ ] Portfolio insight generation
    """)
