#!/usr/bin/env python
"""Debug ETL enrichment for muti-asset_portfolio.csv"""

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
from pagr.fds.services.pipeline import ETLPipeline
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.graph.builder import GraphBuilder
import tempfile
import shutil

def debug_multi_etl():
    """Run ETL pipeline on muti-asset_portfolio"""

    logger.info("=" * 80)
    logger.info("TESTING ETL ON MUTI-ASSET PORTFOLIO")
    logger.info("=" * 80)

    # Initialize ETL Manager
    logger.info("\n1. Initializing ETLManager...")
    etl_manager = ETLManager(config_path="config/config.yaml")
    logger.info("   OK - ETLManager initialized")

    # Read CSV
    csv_path = Path("data/muti-asset_portfolio.csv")
    logger.info(f"\n2. Reading CSV: {csv_path}")
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    logger.info(f"   First few lines:")
    for line in lines[:5]:
        logger.info(f"     {line.rstrip()}")

    # Copy to temp
    logger.info(f"\n3. Creating temp copy...")
    temp_dir = tempfile.mkdtemp()
    temp_csv_path = Path(temp_dir) / "muti-asset_portfolio.csv"
    shutil.copy(csv_path, temp_csv_path)
    logger.info(f"   OK - Temp: {temp_csv_path}")

    # Run ETL pipeline
    logger.info(f"\n4. Running ETL Pipeline...")
    try:
        portfolio_loader = PortfolioLoader()
        graph_builder = GraphBuilder()
        pipeline = ETLPipeline(
            factset_client=etl_manager.factset_client,
            portfolio_loader=portfolio_loader,
            graph_builder=graph_builder
        )
        portfolio, cypher_statements, stats = pipeline.execute(str(temp_csv_path))

        logger.info("   OK - ETL pipeline completed")

        # Log statistics
        logger.info(f"\n5. ETL Pipeline Statistics:")
        logger.info(f"   Portfolios loaded: {stats.portfolios_loaded}")
        logger.info(f"   Positions loaded: {stats.positions_loaded}")
        logger.info(f"   Stocks enriched: {stats.stocks_enriched}")
        logger.info(f"   Bonds enriched: {stats.bonds_enriched}")
        logger.info(f"   Companies enriched: {stats.companies_enriched}")
        logger.info(f"   Graph nodes created: {stats.graph_nodes_created}")
        logger.info(f"   Graph relationships created: {stats.graph_relationships_created}")
        logger.info(f"   Errors: {len(stats.errors)}")

        if stats.errors:
            logger.error("   Errors encountered:")
            for error in stats.errors:
                logger.error(f"     - {error}")

        # Log portfolio details
        if portfolio:
            logger.info(f"\n6. Portfolio Details:")
            logger.info(f"   Name: {portfolio.name}")
            logger.info(f"   Total value: ${portfolio.total_value:,.2f}")
            logger.info(f"   Positions count: {len(portfolio.positions)}")

            logger.info(f"\n7. Position Details:")
            for i, pos in enumerate(portfolio.positions[:5], 1):
                logger.info(f"     [{i}] Ticker: {pos.ticker}, Qty: {pos.quantity}, CUSIP: {pos.cusip}, ISIN: {pos.isin}")
            if len(portfolio.positions) > 5:
                logger.info(f"     ... and {len(portfolio.positions) - 5} more")

        # Count INVESTED_IN statements
        logger.info(f"\n8. Cypher Statements:")
        invested_in_count = sum(1 for stmt in cypher_statements if 'INVESTED_IN' in stmt)
        logger.info(f"   Total statements: {len(cypher_statements)}")
        logger.info(f"   INVESTED_IN statements: {invested_in_count}")
        logger.info(f"   Expected INVESTED_IN: {stats.positions_loaded}")

        if invested_in_count != stats.positions_loaded:
            logger.warning(f"   MISMATCH! Expected {stats.positions_loaded} INVESTED_IN relationships but got {invested_in_count}")

        # Show first few positions to understand the issue
        logger.info(f"\n9. Analyzing position matching:")
        for pos in portfolio.positions[:3]:
            logger.info(f"   Position: ticker={pos.ticker}, cusip={pos.cusip}, isin={pos.isin}")
            if pos.cusip:
                logger.info(f"     → Will match with stocks['{pos.cusip}']")
            elif pos.isin:
                logger.info(f"     → Will match with bonds['{pos.isin}']")
            elif pos.ticker:
                logger.info(f"     → ISSUE: Has ticker but no CUSIP/ISIN - won't find security!")
            else:
                logger.info(f"     → ISSUE: No identifier at all!")

        logger.info(f"\n" + "=" * 80)
        logger.info("DEBUG COMPLETE")
        logger.info("=" * 80)

        # Cleanup
        shutil.rmtree(temp_dir)

    except Exception as e:
        logger.exception(f"Error during ETL pipeline: {e}")
        import traceback
        traceback.print_exc()
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    debug_multi_etl()
