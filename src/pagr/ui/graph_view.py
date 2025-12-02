"""Graph visualization component using PyVis."""

import json
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
from pagr.fds.models.portfolio import Portfolio
from pagr.fds.clients.memgraph_client import MemgraphClient
import tempfile
from pathlib import Path


def display_graph_view(portfolio: Portfolio, memgraph_client: MemgraphClient):
    """Display interactive graph visualization of portfolio relationships."""
    st.subheader("Portfolio Graph - FIBO Relationships")

    col1, col2 = st.columns([3, 1])

    with col2:
        show_countries = st.checkbox("Show Countries", value=False)
        show_executives = False
        show_subsidiaries = False

    with col1:
        with st.spinner("Loading graph data..."):
            try:
                # Build query based on selected options
                query_parts = []
                query_parts.append(f"""
                    MATCH (p:Portfolio {{name: '{portfolio.name}'}})-[:CONTAINS]->(pos:Position)
                    MATCH (pos)-[:ISSUED_BY]->(c:Company)
                    OPTIONAL MATCH (c)-[:HEADQUARTERED_IN]->(country:Country)
                """)

                if show_executives:
                    query_parts.append("OPTIONAL MATCH (exec:Executive)-[:CEO_OF]->(c)")
                else:
                    query_parts.append("OPTIONAL MATCH exec = (n) WHERE 1=0")

                if show_subsidiaries:
                    query_parts.append("OPTIONAL MATCH (c)-[:HAS_SUBSIDIARY]->(sub:Company)")
                else:
                    query_parts.append("OPTIONAL MATCH sub = (n) WHERE 1=0")

                query_parts.append("""
                    RETURN p, pos, c, country, exec, sub
                    LIMIT 100
                """)

                query = "\n".join(query_parts)

                # Execute query
                records = memgraph_client.execute_query(query)

                # Create network
                net = Network(height="700px", width="100%", directed=True, cdn_resources='in_line')
                
                # Configure physics
                physics_options = {
                    "physics": {
                        "enabled": True,
                        "stabilization": {
                            "iterations": 200
                        }
                    }
                }
                net.set_options(json.dumps(physics_options))

                nodes_added = set()
                edges_added = set()

                # Process records and build graph
                for record in records:
                    # Portfolio node
                    if record.get('p'):
                        p = record['p']
                        p_id = f"portfolio_{p.get('name', 'unknown')}"
                        if p_id not in nodes_added:
                            net.add_node(
                                p_id,
                                label=p.get('name', 'Portfolio'),
                                color='#FF6B6B',
                                size=40,
                                title=f"Portfolio: {p.get('name', 'unknown')}"
                            )
                            nodes_added.add(p_id)

                    # Position node
                    if record.get('pos'):
                        pos = record['pos']
                        pos_id = f"pos_{pos.get('ticker', 'unknown')}"
                        if pos_id not in nodes_added:
                            market_val = pos.get('market_value', 0)
                            net.add_node(
                                pos_id,
                                label=f"{pos.get('ticker', 'unknown')}\n${market_val:,.0f}",
                                color='#4ECDC4',
                                size=25,
                                title=f"Position: {pos.get('ticker', 'unknown')}\nMarket Value: ${market_val:,.2f}"
                            )
                            nodes_added.add(pos_id)

                        # Add edge from portfolio to position
                        edge_id = f"{p_id}_contains_{pos_id}"
                        if edge_id not in edges_added:
                            net.add_edge(p_id, pos_id, label='CONTAINS', weight=1)
                            edges_added.add(edge_id)

                    # Company node
                    if record.get('c'):
                        c = record['c']
                        c_id = f"company_{c.get('factset_id', c.get('ticker', 'unknown'))}"
                        if c_id not in nodes_added:
                            net.add_node(
                                c_id,
                                label=c.get('name', 'Company'),
                                color='#95E1D3',
                                size=30,
                                title=f"Company: {c.get('name', 'unknown')}\nSector: {c.get('sector', 'N/A')}"
                            )
                            nodes_added.add(c_id)

                        # Add edge from position to company
                        pos_id = f"pos_{record['pos'].get('ticker', 'unknown')}" if record.get('pos') else None
                        if pos_id:
                            edge_id = f"{pos_id}_issued_by_{c_id}"
                            if edge_id not in edges_added:
                                net.add_edge(pos_id, c_id, label='ISSUED_BY', weight=2)
                                edges_added.add(edge_id)

                    # Country node
                    if show_countries and record.get('country'):
                        country = record['country']
                        country_id = f"country_{country.get('iso_code', 'unknown')}"
                        if country_id not in nodes_added:
                            net.add_node(
                                country_id,
                                label=country.get('iso_code', 'Unknown'),
                                color='#F38181',
                                size=20,
                                title=f"Country: {country.get('iso_code', 'unknown')}"
                            )
                            nodes_added.add(country_id)

                        # Add edge from company to country
                        c_id = f"company_{record['c'].get('factset_id', record['c'].get('ticker', 'unknown'))}" if record.get('c') else None
                        if c_id:
                            edge_id = f"{c_id}_headquartered_in_{country_id}"
                            if edge_id not in edges_added:
                                net.add_edge(c_id, country_id, label='HEADQUARTERED_IN', weight=1)
                                edges_added.add(edge_id)

                    # Executive node
                    if show_executives and record.get('exec'):
                        exec_node = record['exec']
                        exec_id = f"exec_{exec_node.get('fibo_id', exec_node.get('name', 'unknown'))}"
                        if exec_id not in nodes_added:
                            net.add_node(
                                exec_id,
                                label=exec_node.get('name', 'Executive'),
                                color='#AA96DA',
                                size=15,
                                title=f"Executive: {exec_node.get('name', 'unknown')}\nTitle: {exec_node.get('title', 'N/A')}"
                            )
                            nodes_added.add(exec_id)

                        # Add edge from executive to company
                        c_id = f"company_{record['c'].get('factset_id', record['c'].get('ticker', 'unknown'))}" if record.get('c') else None
                        if c_id:
                            edge_id = f"{exec_id}_ceo_of_{c_id}"
                            if edge_id not in edges_added:
                                net.add_edge(exec_id, c_id, label='CEO_OF', weight=1)
                                edges_added.add(edge_id)

                    # Subsidiary node
                    if show_subsidiaries and record.get('sub'):
                        sub = record['sub']
                        sub_id = f"subsidiary_{sub.get('factset_id', sub.get('ticker', 'unknown'))}"
                        if sub_id not in nodes_added:
                            net.add_node(
                                sub_id,
                                label=sub.get('name', 'Subsidiary'),
                                color='#B5D6E6',
                                size=20,
                                title=f"Subsidiary: {sub.get('name', 'unknown')}"
                            )
                            nodes_added.add(sub_id)

                        # Add edge from company to subsidiary
                        c_id = f"company_{record['c'].get('factset_id', record['c'].get('ticker', 'unknown'))}" if record.get('c') else None
                        if c_id:
                            edge_id = f"{c_id}_has_subsidiary_{sub_id}"
                            if edge_id not in edges_added:
                                net.add_edge(c_id, sub_id, label='HAS_SUBSIDIARY', weight=1)
                                edges_added.add(edge_id)

                # Generate and display graph
                html = net.generate_html()

                # Write to temp file and display
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html)
                    temp_path = f.name

                try:
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        components.html(f.read(), height=700)
                finally:
                    Path(temp_path).unlink(missing_ok=True)

                st.caption(f"Graph contains {len(nodes_added)} nodes and {len(edges_added)} relationships")

            except Exception as e:
                st.error(f"Error loading graph: {str(e)}")
                import traceback
                st.text(traceback.format_exc()[:500])
