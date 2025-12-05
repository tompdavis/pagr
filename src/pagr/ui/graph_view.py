"""Graph visualization component using PyVis."""

import json
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
from pagr.fds.models.portfolio import Portfolio
from pagr.fds.clients.memgraph_client import MemgraphClient
import tempfile
from pathlib import Path


def display_graph_view(portfolios, memgraph_client: MemgraphClient):
    """Display interactive graph visualization of portfolio relationships.

    Args:
        portfolios: Single Portfolio object or list of Portfolio objects
        memgraph_client: MemgraphClient instance for database queries
    """
    # Normalize to list for uniform handling
    if isinstance(portfolios, Portfolio):
        portfolios = [portfolios]

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
                # Extract portfolio names for query
                portfolio_names = [p.name for p in portfolios]
                names_list = ", ".join(f"'{name}'" for name in portfolio_names)

                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Graph query for portfolios: {portfolio_names}")

                # Diagnostic: Verify relationship chain exists (DEBUG level)
                test_query_1 = f"""
                    MATCH (p:Portfolio)
                    WHERE p.name IN [{names_list}]
                    RETURN p, count(*) as match_count
                    LIMIT 10
                """
                test_records_1 = memgraph_client.execute_query(test_query_1)
                logger.debug(f"Diagnostic - Portfolios found: {len(test_records_1)} records")

                # Diagnostic: Check Portfolio-Position relationships
                test_query_2 = f"""
                    MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)
                    WHERE p.name IN [{names_list}]
                    RETURN p, pos
                    LIMIT 10
                """
                test_records_2 = memgraph_client.execute_query(test_query_2)
                logger.debug(f"Diagnostic - Portfolio-Position relationships found: {len(test_records_2)} records")

                # Build main query - full graph query
                # Note: INVESTED_IN is optional to support partially-enriched portfolios
                # Note: sec can be Stock or Bond, so use label alternatives (Stock|Bond)
                query_parts = []
                query_parts.append(f"""
                    MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)
                    WHERE p.name IN [{names_list}]
                    OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec:Stock|Bond)
                    OPTIONAL MATCH (sec)-[:ISSUED_BY]->(c:Company)
                    OPTIONAL MATCH (c)-[:HEADQUARTERED_IN]->(country:Country)
                    RETURN p, pos, sec, c, country
                    LIMIT 2000
                """)

                query = "\n".join(query_parts)

                # Log the actual query for debugging
                logger.debug(f"Full Cypher query:\n{query}")

                # Execute query
                records = memgraph_client.execute_query(query)
                logger.info(f"Graph query returned {len(records)} records for {len(portfolio_names)} portfolios")

                if len(records) == 0:
                    logger.warning(f"Query returned 0 records. Query was:\n{query}")
                    st.warning("⚠️ No graph data found. This may indicate the database doesn't have enriched relationship data yet.")

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
                    # Compute IDs for this record upfront
                    p_id = None
                    pos_id = None
                    sec_id = None
                    c_id = None
                    country_id = None

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
                        # Use ticker for stocks, or ticker+cusip for bonds (to make unique)
                        ticker = pos.get('ticker') or ''
                        cusip = pos.get('cusip') or ''
                        if ticker:
                            pos_key = ticker  # Stock position
                        else:
                            pos_key = f"bond_{cusip}"  # Bond position

                        # Make position nodes portfolio-specific by including portfolio name in ID
                        # This ensures different portfolios have separate Position nodes even for same security
                        portfolio_name = p.get('name', 'unknown') if record.get('p') else 'unknown'
                        pos_id = f"pos_{portfolio_name}_{pos_key}"
                        if pos_id not in nodes_added:
                            market_val = pos.get('market_value', 0)
                            pos_label = f"{ticker or cusip}\n${market_val:,.0f}"
                            net.add_node(
                                pos_id,
                                label=pos_label,
                                color='#4ECDC4',
                                size=25,
                                title=f"Position: {ticker or cusip}\nMarket Value: ${market_val:,.2f}\nQuantity: {pos.get('quantity', 0)}"
                            )
                            nodes_added.add(pos_id)

                        # Add edge from portfolio to position
                        if p_id:
                            edge_id = f"{p_id}_contains_{pos_id}"
                            if edge_id not in edges_added:
                                net.add_edge(p_id, pos_id, label='CONTAINS', weight=1)
                                edges_added.add(edge_id)

                    # Security (Stock/Bond) node
                    if record.get('sec'):
                        sec = record['sec']
                        sec_type = sec.get('labels', ['Security'])[0] if sec.get('labels') else 'Security'
                        # Use fibo_id for unique identification
                        sec_fibo = sec.get('fibo_id')
                        if sec_fibo:
                            sec_id = f"security_{sec_fibo}"
                        else:
                            # Fallback: use ticker or cusip
                            sec_id = f"security_{sec.get('ticker') or sec.get('cusip') or 'unknown'}"

                        if sec_id not in nodes_added:
                            sec_label = sec.get('ticker') or sec.get('cusip') or sec.get('isin') or 'Security'
                            net.add_node(
                                sec_id,
                                label=sec_label,
                                color='#FFE66D',
                                size=20,
                                title=f"{sec_type}: {sec_label}"
                            )
                            nodes_added.add(sec_id)

                        # Add edge from position to security
                        if pos_id and sec_id:
                            edge_id = f"{pos_id}_invested_in_{sec_id}"
                            if edge_id not in edges_added:
                                net.add_edge(pos_id, sec_id, label='INVESTED_IN', weight=1)
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

                        # Add edge from security to company
                        if sec_id:
                            edge_id = f"{sec_id}_issued_by_{c_id}"
                            if edge_id not in edges_added:
                                net.add_edge(sec_id, c_id, label='ISSUED_BY', weight=2)
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

                # Extract portfolio nodes to verify multi-portfolio support
                portfolio_nodes = [n for n in nodes_added if n.startswith('portfolio_')]
                logger.info(f"Portfolio nodes in graph: {portfolio_nodes}")
                logger.info(f"Total nodes: {len(nodes_added)}, Portfolio nodes: {len(portfolio_nodes)}, Edges: {len(edges_added)}")

                st.caption(f"Graph contains {len(nodes_added)} nodes and {len(edges_added)} relationships")

            except Exception as e:
                st.error(f"Error loading graph: {str(e)}")
                import traceback
                st.text(traceback.format_exc()[:500])
