"""Test CSV upload simulation (like from Streamlit)."""

import tempfile
from pathlib import Path
from pagr.fds.loaders.portfolio_loader import PortfolioLoader


def test_upload_csv_with_spaces():
    """Simulate Streamlit CSV upload with space-separated column names."""
    print("Testing Streamlit upload simulation with spaces...\n")

    # Create CSV content exactly as it would come from Streamlit upload
    csv_content = """Ticker,Quantity,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
"""

    # Write to a temp file (simulating what Streamlit does)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        # Load portfolio (this is what happens in etl_manager.process_uploaded_csv)
        portfolio = PortfolioLoader.load(tmp_path)

        print(f"[PASS] Successfully loaded portfolio from uploaded CSV")
        print(f"Portfolio: {portfolio.name}")
        print(f"Positions: {len(portfolio.positions)}")
        print(f"Total book value: ${portfolio.total_value:,.2f}\n")

        for pos in portfolio.positions:
            print(f"  {pos.ticker}: {pos.quantity} shares @ ${pos.book_value/pos.quantity:.2f}")

    except Exception as e:
        print(f"[FAIL] Failed to load uploaded CSV: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_upload_csv_mixed_headers():
    """Test upload with mixed case and spaces in headers."""
    print("\n\nTesting mixed headers with unusual formatting...\n")

    csv_content = """TICKER,QUANTITY,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path)
        print(f"[PASS] Successfully loaded with mixed case headers")
        print(f"Position: {portfolio.positions[0].ticker}\n")

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_upload_csv_underscore_headers():
    """Test upload with underscore headers."""
    print("Testing underscore-formatted headers...\n")

    csv_content = """ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path)
        print(f"[PASS] Successfully loaded with underscore headers")
        print(f"Position: {portfolio.positions[0].ticker}\n")

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_csv_with_extra_columns():
    """Test CSV with additional columns (should be ignored)."""
    print("Testing CSV with extra columns...\n")

    csv_content = """Ticker,Quantity,Book Value,Extra Column,Security Type,ISIN,CUSIP,Another Extra
AAPL-US,100,19000.00,ignored,Common Stock,US0378331005,037833100,also ignored
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        portfolio = PortfolioLoader.load(tmp_path)
        print(f"[PASS] Successfully loaded CSV with extra columns (ignored)")
        print(f"Position: {portfolio.positions[0].ticker}\n")

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("=" * 60)
    print("Testing CSV Upload Scenarios (Streamlit Simulation)")
    print("=" * 60 + "\n")

    test_upload_csv_with_spaces()
    test_upload_csv_mixed_headers()
    test_upload_csv_underscore_headers()
    test_csv_with_extra_columns()

    print("=" * 60)
    print("[PASS] All upload simulation tests passed!")
    print("=" * 60)
