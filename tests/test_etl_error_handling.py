"""Test ETL pipeline error handling."""

import tempfile
from pathlib import Path
from pagr.etl_manager import ETLManager


def test_credentials_file_reading():
    """Test that ETLManager can read credentials file."""
    print("Testing credentials file reading...")

    # Check if credentials file exists
    cred_path = Path("fds-api.key")
    if cred_path.exists():
        print("[INFO] Credentials file exists")
        etl_manager = ETLManager()
        try:
            client = etl_manager.factset_client
            assert client is not None
            print("[PASS] Successfully initialized FactSet client with credentials")
        except Exception as e:
            print(f"[FAIL] Failed to initialize FactSet client: {e}")
            raise
    else:
        print("[WARN] Credentials file not found (expected in fresh setup)")


def test_memgraph_client_initialization():
    """Test that Memgraph client initializes correctly."""
    print("\nTesting Memgraph client initialization...")

    etl_manager = ETLManager()

    try:
        memgraph_client = etl_manager.memgraph_client
        assert memgraph_client is not None
        assert memgraph_client.host == "127.0.0.1"
        assert memgraph_client.port == 7687
        print("[PASS] Memgraph client initialized with correct configuration")
    except Exception as e:
        print(f"[FAIL] Memgraph client initialization failed: {e}")
        raise


def test_database_connection_check():
    """Test that connection check handles Memgraph not running gracefully."""
    print("\nTesting database connection check...")

    etl_manager = ETLManager()

    # This should return False if Memgraph is not running
    result = etl_manager.check_connection()
    if result:
        print("[PASS] Connected to Memgraph successfully")
    else:
        print("[INFO] Memgraph not available (expected in test environment)")
        print("[PASS] Connection check handled gracefully")


def test_invalid_csv_file():
    """Test that portfolio loader handles invalid CSV files."""
    print("\nTesting invalid CSV file handling...")

    # Create invalid CSV
    csv_content = """Invalid,CSV,Format
without,required,columns
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        from pagr.fds.loaders.portfolio_loader import PortfolioLoader, PortfolioLoaderError

        try:
            portfolio = PortfolioLoader.load(temp_path)
            print("[FAIL] Should have raised PortfolioLoaderError for invalid CSV")
        except PortfolioLoaderError as e:
            if "book_value" in str(e).lower():
                print(f"[PASS] Correctly raised PortfolioLoaderError for missing book_value")
            else:
                print(f"[INFO] Raised PortfolioLoaderError: {str(e)[:100]}...")
    finally:
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("Testing ETL pipeline error handling...\n")

    test_credentials_file_reading()
    test_memgraph_client_initialization()
    test_database_connection_check()
    test_invalid_csv_file()

    print("\n[PASS] All error handling tests completed!")
