#!/usr/bin/env python
"""Test INVESTED_IN - actually execute in Memgraph."""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pagr.etl_manager import ETLManager

def test():
    logger.info("=" * 80)
    logger.info("TESTING INVESTED_IN - WITH DATABASE EXECUTION")
    logger.info("=" * 80)

    # Use ETLManager which EXECUTES statements to database
    etl_manager = ETLManager(config_path="config/config.yaml")

    logger.info("\n1. Ensuring Memgraph connection...")
    if not etl_manager.memgraph_client.is_connected:
        etl_manager.memgraph_client.connect()
    logger.info("   ✓ Connected to Memgraph")

    # Create a fake file object for the portfolio
    csv_path = Path("data/sample_portfolio.csv")

    class FakeFile:
        def __init__(self, path):
            self.path = path
        def getvalue(self):
            return self.path.read_bytes()

    logger.info("\n2. Processing sample_portfolio.csv through ETL Manager...")
    fake_file = FakeFile(csv_path)
    portfolio, stats = etl_manager.process_uploaded_csv(fake_file, portfolio_name="test_portfolio")
    logger.info(f"   ✓ Portfolio processed")
    logger.info(f"   - Positions: {stats.positions_loaded}")
    logger.info(f"   - Stocks enriched: {stats.stocks_enriched}")
    logger.info(f"   - Relationships created: {stats.graph_relationships_created}")
    logger.info(f"   - Errors: {len(stats.errors)}")

    # Now query the database to verify INVESTED_IN relationships exist
    logger.info("\n3. Querying database for INVESTED_IN relationships...")

    query = """
    MATCH (pos:Position)-[:INVESTED_IN]->(sec:Stock)
    RETURN count(*) as invested_in_count,
           collect(pos.ticker) as position_tickers,
           collect(sec.ticker) as stock_tickers
    """

    try:
        result = etl_manager.memgraph_client.execute_query(query)
        if result:
            record = result[0]
            invested_in_count = record.get('invested_in_count', 0)
            logger.info(f"   ✓ Found {invested_in_count} INVESTED_IN relationships")

            if invested_in_count > 0:
                logger.info(f"   Position tickers: {record.get('position_tickers')}")
                logger.info(f"   Stock tickers: {record.get('stock_tickers')}")

                if invested_in_count == stats.positions_loaded:
                    logger.info(f"\n✅ SUCCESS: All {invested_in_count} positions have INVESTED_IN relationships!")
                    return True
                else:
                    logger.error(f"\n❌ MISMATCH: Expected {stats.positions_loaded}, got {invested_in_count}")
                    return False
            else:
                logger.error(f"\n❌ FAILED: No INVESTED_IN relationships found in database!")
                return False
    except Exception as e:
        logger.error(f"   Error querying database: {e}")
        return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
