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
