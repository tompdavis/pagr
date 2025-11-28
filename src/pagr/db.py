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
                    c.ticker = $ticker,
                    c.country_code = $country_code,
                    c.country_of_risk = $country_of_risk
                
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
                            sector=meta['sector'],
                            country_code=meta.get('country_code', 'Unknown'),
                            country_of_risk=meta.get('country_of_risk', 'Unknown'))
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

def check_portfolio_exists(name: str) -> bool:
    """Checks if a portfolio with the given name exists in the database."""
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run("MATCH (p:Portfolio {name: $name}) RETURN p", name=name)
            return result.single() is not None
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
    finally:
        driver.close()

def get_portfolio(name: str) -> Portfolio:
    """
    Retrieves a Portfolio object from the database.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            # Fetch Portfolio metadata
            p_result = session.run("MATCH (p:Portfolio {name: $name}) RETURN p", name=name)
            p_record = p_result.single()
            if not p_record:
                raise ValueError(f"Portfolio {name} not found in database")
            
            # Fetch Positions
            query = """
            MATCH (p:Portfolio {name: $name})-[:CONTAINS]->(pos:Position)
            RETURN pos.ticker as ticker, pos.qty as qty, pos.book_val as book_val
            """
            pos_result = session.run(query, name=name)
            
            positions = []
            from pagr.portfolio import Position # Import here to avoid circular dependency if any
            
            for record in pos_result:
                positions.append(Position(
                    ticker=record['ticker'],
                    quantity=record['qty'],
                    book_value=record['book_val']
                ))
            
            # We don't store currency or last_updated in DB currently, so use defaults or placeholders
            # If we want to store them, we need to update load_portfolio to save them on the Portfolio node
            return Portfolio(
                name=name,
                currency="USD", # Default
                last_updated="", # Default
                positions=positions
            )
    finally:
        driver.close()
