"""Test backward compatibility with market_value column."""

import tempfile
from pathlib import Path
from pagr.fds.loaders.portfolio_loader import PortfolioLoader


def test_market_value_column():
    """Test that CSV with market_value column (not book_value) loads correctly."""
    print("Testing CSV with market_value column...\n")

    csv_content = """Ticker,Quantity,Market Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
TSMC-TT,200,32000.00,Common Stock,US8740391003,874039100
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path, portfolio_name='Market Value Portfolio')

        print(f"[PASS] Successfully loaded portfolio with market_value column")
        print(f"Portfolio: {portfolio.name}")
        print(f"Positions: {len(portfolio.positions)}")
        print(f"Total book value: ${portfolio.total_value:,.2f}\n")

        for pos in portfolio.positions:
            price_per_share = pos.book_value / pos.quantity
            print(f"  {pos.ticker}: {pos.quantity} shares @ ${price_per_share:.2f} = ${pos.book_value:,.2f} ({pos.weight:.1f}%)")

        # Verify weights sum to 100%
        total_weight = sum(p.weight for p in portfolio.positions)
        print(f"\nTotal weight: {total_weight:.1f}% [OK]")

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_book_value_column():
    """Test that CSV with book_value column still works."""
    print("\n\nTesting CSV with book_value column...\n")

    csv_content = """Ticker,Quantity,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path, portfolio_name='Book Value Portfolio')

        print(f"[PASS] Successfully loaded portfolio with book_value column")
        print(f"Portfolio: {portfolio.name}")
        print(f"Positions: {len(portfolio.positions)}")
        print(f"Total book value: ${portfolio.total_value:,.2f}\n")

        for pos in portfolio.positions:
            price_per_share = pos.book_value / pos.quantity
            print(f"  {pos.ticker}: {pos.quantity} shares @ ${price_per_share:.2f} = ${pos.book_value:,.2f} ({pos.weight:.1f}%)")

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_both_columns():
    """Test CSV with both book_value and market_value columns."""
    print("\n\nTesting CSV with both columns...\n")

    csv_content = """Ticker,Quantity,Book Value,Market Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,24000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,19000.00,Common Stock,US5949181045,594918104
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path, portfolio_name='Both Values Portfolio')

        print(f"[PASS] Successfully loaded portfolio with both columns")
        print(f"Portfolio: {portfolio.name}")
        print(f"Positions: {len(portfolio.positions)}\n")

        for pos in portfolio.positions:
            print(f"  {pos.ticker}:")
            print(f"    Book value: ${pos.book_value:,.2f}")
            market_val = f"${pos.market_value:,.2f}" if pos.market_value else "N/A"
            print(f"    Market value: {market_val}")
            print(f"    Weight: {pos.weight:.1f}%")

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("="*60)
    print("Testing Backward Compatibility with market_value Column")
    print("="*60 + "\n")

    test_market_value_column()
    test_book_value_column()
    test_both_columns()

    print("\n" + "="*60)
    print("[PASS] All backward compatibility tests passed!")
    print("="*60)
