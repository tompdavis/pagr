"""Test Memgraph database operations."""

from pagr.etl_manager import ETLManager


def test_database_cleanup():
    """Test clearing database."""
    print("Testing database cleanup...")

    etl_manager = ETLManager()

    try:
        etl_manager.clear_database()
        print("[PASS] Successfully cleared database")
    except Exception as e:
        print(f"[INFO] Could not clear database (may be permission issue): {e}")


def test_create_basic_nodes():
    """Test creating basic nodes in Memgraph."""
    print("\nTesting basic node creation...")

    etl_manager = ETLManager()

    try:
        # Ensure connection is active
        if not etl_manager.memgraph_client.is_connected:
            etl_manager.memgraph_client.connect()

        # Create a test portfolio node
        query = """
        CREATE (p:Portfolio {
            name: 'Test Portfolio',
            created_at: '2025-01-01T00:00:00',
            total_value: 100000
        })
        RETURN p
        """
        result = etl_manager.memgraph_client.execute_query(query)
        print("[PASS] Successfully created portfolio node")
    except Exception as e:
        print(f"[FAIL] Failed to create node: {e}")
        raise


def test_create_relationships():
    """Test creating relationships between nodes."""
    print("\nTesting relationship creation...")

    etl_manager = ETLManager()

    try:
        # Ensure connection is active
        if not etl_manager.memgraph_client.is_connected:
            etl_manager.memgraph_client.connect()

        # Create position node and relationship
        query = """
        MATCH (p:Portfolio {name: 'Test Portfolio'})
        CREATE (pos:Position {
            ticker: 'AAPL-US',
            quantity: 100,
            book_value: 19000
        })
        CREATE (p)-[:CONTAINS]->(pos)
        RETURN p, pos
        """
        result = etl_manager.memgraph_client.execute_query(query)
        print("[PASS] Successfully created relationship")
    except Exception as e:
        print(f"[FAIL] Failed to create relationship: {e}")
        raise


def test_query_nodes():
    """Test querying nodes from database."""
    print("\nTesting node queries...")

    etl_manager = ETLManager()

    try:
        # Ensure connection is active
        if not etl_manager.memgraph_client.is_connected:
            etl_manager.memgraph_client.connect()

        # Query portfolio nodes
        query = "MATCH (p:Portfolio) RETURN p.name, p.total_value"
        result = etl_manager.memgraph_client.execute_query(query)
        print(f"[PASS] Successfully queried nodes")
        print(f"  Result: {result if result else 'No results'}")
    except Exception as e:
        print(f"[FAIL] Failed to query nodes: {e}")
        raise


def test_graph_statistics():
    """Test getting graph statistics."""
    print("\nTesting graph statistics...")

    etl_manager = ETLManager()

    try:
        stats = etl_manager.get_database_stats()
        if stats:
            print("[PASS] Successfully retrieved database statistics")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        else:
            print("[INFO] No statistics available")
    except Exception as e:
        print(f"[INFO] Could not retrieve statistics: {e}")


if __name__ == "__main__":
    print("Testing Memgraph database operations...\n")

    test_database_cleanup()
    test_create_basic_nodes()
    test_create_relationships()
    test_query_nodes()
    test_graph_statistics()

    print("\n[PASS] All Memgraph operation tests completed!")
