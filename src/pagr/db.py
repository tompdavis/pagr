import os
from neo4j import GraphDatabase
from pagr.portfolio import Portfolio
from pagr.market_data import fetch_company_metadata

# Configuration
MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")

def get_driver():
    """Creates and returns a Neo4j driver instance."""
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER or MEMGRAPH_PASSWORD else None
    return GraphDatabase.driver(MEMGRAPH_URI, auth=auth)

def load_portfolio(portfolio: Portfolio):
    """
    Loads the portfolio into Memgraph.
    This clears the existing relationships for this portfolio name and repopulates them.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            # 1. Create Portfolio Node
            session.run("MERGE (p:Portfolio {name: $name})", name=portfolio.name)
            
            # 2. Clear existing positions for this portfolio to ensure sync
            # We detach delete the positions connected to this portfolio
            session.run("""
                MATCH (p:Portfolio {name: $name})-[r:CONTAINS]->(pos:Position)
                DETACH DELETE pos
            """, name=portfolio.name)
            
            # 3. Add Positions
            for pos in portfolio.positions:
                meta = fetch_company_metadata(pos.ticker)
                company_id = meta['lei'] if meta['lei'] else f"ID_{pos.ticker}"
                
                query = """
                MATCH (p:Portfolio {name: $name})
                
                CREATE (pos:Position {ticker: $ticker, qty: $qty, book_val: $book_val})
                
                MERGE (c:Company {id: $company_id})
                SET c.name = $legal_name,
                    c.lei = $lei,
                    c.sector = $sector,
                    c.ticker = $ticker
                
                MERGE (p)-[:CONTAINS]->(pos)
                MERGE (pos)-[:IS_INVESTED_IN]->(c)
                """
                
                session.run(query, 
                            name=portfolio.name,
                            ticker=pos.ticker, 
                            qty=pos.quantity, 
                            book_val=pos.book_value,
                            company_id=company_id,
                            legal_name=meta['legal_name'],
                            lei=meta['lei'],
                            sector=meta['sector'])
    finally:
        driver.close()

def get_portfolio_view(portfolio_name: str):
    """
    Queries the database to construct the portfolio view.
    Returns a list of dictionaries containing position details.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            query = """
            MATCH (p:Portfolio {name: $name})-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company)
            RETURN pos.ticker as ticker, pos.qty as quantity, pos.book_val as book_value, c.sector as sector
            """
            result = session.run(query, name=portfolio_name)
            return [record.data() for record in result]
    finally:
        driver.close()

def get_graph_data(portfolio_name: str):
    """
    Queries the database to retrieve nodes and edges for the graph view.
    Returns a tuple of (nodes, edges) suitable for streamlit-agraph.
    """
    driver = get_driver()
    nodes_data = []
    edges_data = []
    
    try:
        with driver.session() as session:
            # 1. Fetch Portfolio Node
            result = session.run("MATCH (p:Portfolio {name: $name}) RETURN p", name=portfolio_name)
            for record in result:
                p = record['p']
                nodes_data.append({
                    "id": f"PORTFOLIO_{portfolio_name}",
                    "label": portfolio_name,
                    "type": "Portfolio",
                    "color": "#FF5733", # Orange
                    "size": 25
                })

            # 2. Fetch Positions and relationships
            query = """
            MATCH (p:Portfolio {name: $name})-[:CONTAINS]->(pos:Position)
            RETURN pos.ticker as ticker, pos.qty as qty, pos.book_val as book_val
            """
            result = session.run(query, name=portfolio_name)
            for record in result:
                ticker = record['ticker']
                qty = record['qty']
                book_val = record['book_val']
                pos_id = f"POS_{ticker}"
                
                nodes_data.append({
                    "id": pos_id,
                    "label": f"{ticker}\n({qty})",
                    "type": "Position",
                    "color": "#33FF57", # Green
                    "size": 15,
                    "title": f"Ticker: {ticker}<br>Quantity: {qty}<br>Book Value: {book_val}"
                })
                
                edges_data.append({
                    "source": f"PORTFOLIO_{portfolio_name}",
                    "target": pos_id,
                    "label": "CONTAINS"
                })

            # 3. Fetch Companies and relationships
            query = """
            MATCH (p:Portfolio {name: $name})-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company)
            RETURN pos.ticker as ticker, c.name as name, c.sector as sector, c.lei as lei, c.id as cid
            """
            result = session.run(query, name=portfolio_name)
            for record in result:
                ticker = record['ticker']
                c_name = record['name']
                sector = record['sector']
                lei = record['lei']
                cid = record['cid']
                
                # Ensure Company Node exists (might be shared)
                # We use cid as ID
                # Check if we already added this company node to avoid duplicates in list
                if not any(n['id'] == cid for n in nodes_data):
                    nodes_data.append({
                        "id": cid,
                        "label": c_name,
                        "type": "Company",
                        "color": "#3357FF", # Blue
                        "size": 20,
                        "title": f"Name: {c_name}<br>Sector: {sector}<br>LEI: {lei}"
                    })
                
                edges_data.append({
                    "source": f"POS_{ticker}",
                    "target": cid,
                    "label": "INVESTED_IN"
                })
                
    finally:
        driver.close()
        
    return nodes_data, edges_data
