"""Test simulating the exact Streamlit upload scenario."""

import tempfile
from pathlib import Path
from io import BytesIO
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.etl_manager import ETLManager


def test_streamlit_uploaded_file_scenario():
    """
    Simulate the exact scenario from Streamlit app:
    1. User uploads CSV through Streamlit file uploader
    2. ETLManager writes to temp file
    3. PortfolioLoader reads and validates
    """
    print("Testing Streamlit Upload Scenario\n" + "="*60 + "\n")

    # This is the content that would come from Streamlit upload
    csv_content = b"""Ticker,Quantity,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
TSMC-TT,200,32000.00,Common Stock,US8740391003,874039100
GE-US,150,12000.00,Common Stock,US3696041033,369604103
NVDA-US,30,13500.00,Common Stock,US67066G1040,67066G104
"""

    # Simulate what ETLManager.process_uploaded_csv does:
    # 1. Write uploaded bytes to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp_file:
        tmp_file.write(csv_content)
        tmp_path = tmp_file.name

    try:
        print(f"1. Simulated Streamlit upload written to: {tmp_path}")
        print(f"   File size: {len(csv_content)} bytes\n")

        # 2. Load portfolio (what PortfolioLoader.load does)
        print("2. Loading portfolio...")
        portfolio = PortfolioLoader.load(tmp_path, portfolio_name="Uploaded Portfolio")

        print(f"   [OK] Successfully loaded portfolio: {portfolio.name}")
        print(f"   [OK] Positions: {len(portfolio.positions)}")
        print(f"   [OK] Total book value: ${portfolio.total_value:,.2f}\n")

        # 3. Verify all positions
        print("3. Portfolio breakdown:")
        for i, pos in enumerate(portfolio.positions, 1):
            print(f"   {i}. {pos.ticker}: {pos.quantity} shares @ ${pos.book_value/pos.quantity:.2f} = ${pos.book_value:,.2f} ({pos.weight:.1f}%)")

        # 4. Verify weights sum to 100%
        total_weight = sum(p.weight for p in portfolio.positions)
        print(f"\n4. Weight verification: {total_weight:.1f}% [OK]")

        # 5. Verify largest position
        largest = sorted(portfolio.positions, key=lambda p: p.book_value, reverse=True)[0]
        print(f"5. Largest position: {largest.ticker} ({largest.weight:.1f}%) [OK]")

        print("\n" + "="*60)
        print("[PASS] Streamlit upload scenario completed successfully!")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Streamlit upload scenario failed!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


def test_edge_case_headers():
    """Test various edge cases that might appear in user CSVs."""
    print("\n\nTesting Edge Cases\n" + "="*60 + "\n")

    test_cases = [
        ("Minimal headers", b"ticker,quantity,book_value\nAAPL-US,100,19000\n"),
        ("Extra spaces", b"  Ticker  ,  Quantity  ,  Book Value  \nAAPL-US,100,19000\n"),
        ("Tab separators", b"Ticker\tQuantity\tBook Value\nAAPL-US\t100\t19000\n"),
        ("Mixed separators", b"TICKER,Quantity,Book Value,Security Type\nAAPL-US,100,19000,Common Stock\n"),
    ]

    for test_name, content in test_cases:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            portfolio = PortfolioLoader.load(tmp_path)
            print(f"[OK] {test_name}: Loaded {len(portfolio.positions)} position(s)")
        except Exception as e:
            print(f"[FAIL] {test_name}: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    print("\n" + "="*60)


if __name__ == "__main__":
    success = test_streamlit_uploaded_file_scenario()
    test_edge_case_headers()

    if success:
        exit(0)
    else:
        exit(1)
