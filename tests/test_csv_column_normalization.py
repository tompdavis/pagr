"""Test CSV column normalization with spaces and underscores."""

import tempfile
from pathlib import Path
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
from pagr.fds.loaders.validator import PositionValidator, ValidationError


def test_validate_headers_with_spaces():
    """Test that headers with spaces are normalized correctly."""
    # Headers with spaces
    headers = ["Ticker", "Quantity", "Book Value", "Security Type", "ISIN", "CUSIP"]

    # This should not raise an error
    try:
        PositionValidator.validate_headers(headers)
        print("[PASS] Headers with spaces validated successfully")
    except ValidationError as e:
        print(f"[FAIL] Headers with spaces failed: {e}")
        raise


def test_validate_headers_with_underscores():
    """Test that headers with underscores are normalized correctly."""
    # Headers with underscores
    headers = ["ticker", "quantity", "book_value", "security_type", "isin", "cusip"]

    # This should not raise an error
    try:
        PositionValidator.validate_headers(headers)
        print("[PASS] Headers with underscores validated successfully")
    except ValidationError as e:
        print(f"[FAIL] Headers with underscores failed: {e}")
        raise


def test_validate_headers_mixed():
    """Test that mixed headers (spaces and underscores) are normalized correctly."""
    # Headers with mixed spaces and underscores
    headers = ["Ticker", "quantity", "Book Value", "security_type", "isin", "cusip"]

    # This should not raise an error
    try:
        PositionValidator.validate_headers(headers)
        print("[PASS] Mixed headers validated successfully")
    except ValidationError as e:
        print(f"[FAIL] Mixed headers failed: {e}")
        raise


def test_load_csv_with_spaces():
    """Test loading CSV file with space-separated column names."""
    # Create temporary CSV with spaces in headers
    csv_content = """Ticker,Quantity,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        positions = PortfolioLoader._read_csv(Path(temp_path))
        assert len(positions) == 2
        assert positions[0].ticker == "AAPL-US"
        assert positions[0].quantity == 100.0
        assert positions[0].book_value == 19000.00
        print(f"[PASS] CSV with spaces loaded successfully: {len(positions)} positions")
    except Exception as e:
        print(f"[FAIL] CSV with spaces failed: {e}")
        raise
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_load_csv_with_underscores():
    """Test loading CSV file with underscore-separated column names."""
    # Create temporary CSV with underscores in headers
    csv_content = """ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        positions = PortfolioLoader._read_csv(Path(temp_path))
        assert len(positions) == 2
        assert positions[0].ticker == "AAPL-US"
        assert positions[0].quantity == 100.0
        assert positions[0].book_value == 19000.00
        print(f"[PASS] CSV with underscores loaded successfully: {len(positions)} positions")
    except Exception as e:
        print(f"[FAIL] CSV with underscores failed: {e}")
        raise
    finally:
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("Testing CSV column normalization...\n")

    test_validate_headers_with_spaces()
    test_validate_headers_with_underscores()
    test_validate_headers_mixed()
    test_load_csv_with_spaces()
    test_load_csv_with_underscores()

    print("\n[PASS] All CSV column normalization tests passed!")
