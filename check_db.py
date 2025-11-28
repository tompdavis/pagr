
from pagr.db import get_driver

def check_db():
    print("Checking database content...")
    driver = get_driver()
    try:
        with driver.session() as session:
            # Check Portfolios
            result = session.run("MATCH (p:Portfolio) RETURN p.name, p.id")
            portfolios = [record.data() for record in result]
            print(f"Portfolios found: {portfolios}")
            
            # Check Positions for 'USD Odlum Portfolio'
            # Note: The schema might use 'name' or 'id' for the portfolio.
            # Let's check both.
            
            query = """
            MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)
            RETURN p.name, count(pos) as position_count
            """
            result = session.run(query)
            counts = [record.data() for record in result]
            print(f"Position counts: {counts}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    check_db()
