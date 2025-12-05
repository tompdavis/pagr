#!/usr/bin/env python
"""Debug test - show actual INVESTED_IN Cypher statements."""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pagr.etl_manager import ETLManager
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.graph.builder import GraphBuilder
from pagr.fds.services.pipeline import ETLPipeline

def test():
    etl_manager = ETLManager(config_path="config/config.yaml")
    csv_path = Path("data/sample_portfolio.csv")

    portfolio_loader = PortfolioLoader()
    graph_builder = GraphBuilder()
    pipeline = ETLPipeline(
        factset_client=etl_manager.factset_client,
        portfolio_loader=portfolio_loader,
        graph_builder=graph_builder
    )

    portfolio, cypher_statements, stats = pipeline.execute(str(csv_path))

    print("\n" + "=" * 80)
    print("ALL CYPHER STATEMENTS")
    print("=" * 80)

    for i, stmt in enumerate(cypher_statements, 1):
        print(f"\n[{i}] {stmt}")

    print("\n" + "=" * 80)
    print("INVESTED_IN STATEMENTS ONLY")
    print("=" * 80)

    invested_in = [s for s in cypher_statements if 'INVESTED_IN' in s]
    print(f"\nFound {len(invested_in)} INVESTED_IN statements:\n")
    for i, stmt in enumerate(invested_in, 1):
        print(f"[{i}] {stmt}\n")

if __name__ == "__main__":
    test()
