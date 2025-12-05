#!/usr/bin/env python
"""Test script to verify INVESTED_IN relationships are created."""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pagr.etl_manager import ETLManager
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.graph.builder import GraphBuilder
from pagr.fds.services.pipeline import ETLPipeline

def test_invested_in():
    """Test INVESTED_IN relationship creation."""

    logger.info("=" * 80)
    logger.info("TESTING INVESTED_IN RELATIONSHIPS WITH SAMPLE PORTFOLIO")
    logger.info("=" * 80)

    # Step 1: Initialize
    logger.info("\n1. Initializing ETL Manager...")
    etl_manager = ETLManager(config_path="config/config.yaml")
    logger.info("   ✓ ETLManager initialized")

    # Step 2: Load portfolio
    logger.info("\n2. Loading sample_portfolio.csv...")
    csv_path = Path("data/sample_portfolio.csv")
    portfolio = PortfolioLoader.load(str(csv_path))
    logger.info(f"   ✓ Loaded portfolio: {portfolio.name}")
    logger.info(f"   ✓ Positions: {len(portfolio.positions)}")

    # Step 3: Show position details
    logger.info("\n3. Position Details:")
    for i, pos in enumerate(portfolio.positions, 1):
        logger.info(f"   [{i}] {pos.ticker}: CUSIP={pos.cusip}, ISIN={pos.isin}")

    # Step 4: Run ETL pipeline
    logger.info("\n4. Running ETL Pipeline...")
    portfolio_loader = PortfolioLoader()
    graph_builder = GraphBuilder()
    pipeline = ETLPipeline(
        factset_client=etl_manager.factset_client,
        portfolio_loader=portfolio_loader,
        graph_builder=graph_builder
    )

    try:
        portfolio, cypher_statements, stats = pipeline.execute(str(csv_path))
        logger.info("   ✓ ETL pipeline completed")

        # Step 5: Show stats
        logger.info("\n5. ETL Statistics:")
        logger.info(f"   Positions loaded: {stats.positions_loaded}")
        logger.info(f"   Stocks enriched: {stats.stocks_enriched}")
        logger.info(f"   Graph nodes created: {stats.graph_nodes_created}")
        logger.info(f"   Graph relationships created: {stats.graph_relationships_created}")
        logger.info(f"   Errors: {len(stats.errors)}")

        if stats.errors:
            for error in stats.errors:
                logger.error(f"     - {error}")

        # Step 6: Count INVESTED_IN statements
        logger.info("\n6. Cypher Statements Analysis:")
        invested_in_count = sum(1 for stmt in cypher_statements if 'INVESTED_IN' in stmt)
        logger.info(f"   Total statements: {len(cypher_statements)}")
        logger.info(f"   INVESTED_IN statements: {invested_in_count}")
        logger.info(f"   Expected INVESTED_IN: {stats.positions_loaded}")

        if invested_in_count > 0:
            logger.info("\n   Sample INVESTED_IN statements:")
            for stmt in cypher_statements:
                if 'INVESTED_IN' in stmt:
                    logger.info(f"     {stmt[:120]}...")
        else:
            logger.error("\n   ⚠️ NO INVESTED_IN STATEMENTS FOUND!")

        # Step 7: Check internal dictionaries
        logger.info("\n7. Analyzing Pipeline Dictionaries:")

        # We need to trace through the pipeline internals
        # Run pipeline again but capture the position_to_security dict
        logger.info("   Re-running pipeline to capture internal state...")

        portfolio2, cypher_statements2, stats2 = pipeline.execute(str(csv_path))

        # Check if stocks were enriched
        logger.info(f"\n   Stocks enriched: {stats2.stocks_enriched}")
        logger.info(f"   Stocks enriched should match positions: {stats2.stocks_enriched == len(portfolio2.positions)}")

        # Step 8: Final verdict
        logger.info("\n8. Test Result:")
        if invested_in_count == len(portfolio.positions):
            logger.info("   ✅ SUCCESS: INVESTED_IN relationships created for all positions")
            return True
        else:
            logger.error(f"   ❌ FAILED: Expected {len(portfolio.positions)} INVESTED_IN, got {invested_in_count}")
            return False

    except Exception as e:
        logger.exception(f"Error during ETL pipeline: {e}")
        return False

if __name__ == "__main__":
    success = test_invested_in()
    sys.exit(0 if success else 1)
