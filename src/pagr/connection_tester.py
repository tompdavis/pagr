"""Connection testing utilities for external services."""

import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


def test_memgraph_connection(memgraph_client) -> Tuple[bool, str]:
    """Test Memgraph connection by querying portfolio list.

    Args:
        memgraph_client: MemgraphClient instance

    Returns:
        Tuple of (success: bool, message: str)
        - If successful: (True, "Connected! Found X portfolios")
        - If failed: (False, "Error message")
    """
    try:
        # Ensure connection is established
        if not memgraph_client.is_connected:
            memgraph_client.connect()

        # Query to get portfolio list
        query = "MATCH (p:Portfolio) RETURN p.name AS name ORDER BY p.name"
        results = memgraph_client.execute_query(query)

        # Count portfolios
        portfolio_count = len(results)

        message = f"✅ Memgraph Connected! Found {portfolio_count} portfolio(s)"
        logger.info(f"Memgraph connection test passed: {message}")

        return True, message

    except Exception as e:
        error_msg = f"❌ Memgraph Connection Failed: {str(e)}"
        logger.error(f"Memgraph connection test failed: {error_msg}")
        return False, error_msg


def test_factset_connection(factset_client) -> Tuple[bool, str]:
    """Test FactSet connection by fetching FDS stock price.

    Args:
        factset_client: FactSetClient instance

    Returns:
        Tuple of (success: bool, message: str)
        - If successful: (True, "Connected! FDS Price: $XXX.XX")
        - If failed: (False, "Error message")
    """
    try:
        # Fetch FDS stock price as a test
        results = factset_client.get_last_close_prices(["FDS-US"])

        # Parse response to extract price
        if "data" in results and len(results["data"]) > 0:
            fds_data = results["data"][0]
            price = fds_data.get("price")

            if price is not None:
                message = f"✅ FactSet Connected! FDS Price: ${price:.2f}"
                logger.info(f"FactSet connection test passed: {message}")
                return True, message

        # If we got here, something unexpected happened
        error_msg = f"❌ FactSet: Unexpected response format"
        logger.warning(f"FactSet connection test unexpected response: {results}")
        return False, error_msg

    except Exception as e:
        error_msg = f"❌ FactSet Connection Failed: {str(e)}"
        logger.error(f"FactSet connection test failed: {error_msg}")
        return False, error_msg


def test_llm_connection(llm_config: Dict[str, Any]) -> Tuple[bool, str]:
    """Test LLM connection (placeholder - not implemented yet).

    Args:
        llm_config: LLM configuration dict

    Returns:
        Tuple of (False, "Not implemented yet")
    """
    message = "⚠️ LLM: Not Implemented Yet"
    logger.info("LLM connection test: not yet implemented")
    return False, message


def test_all_connections(etl_manager) -> Dict[str, Dict[str, str]]:
    """Test all connections and return status dict.

    Args:
        etl_manager: ETLManager instance with clients

    Returns:
        Dict with connection status for each service:
        {
            "memgraph": {"status": "success"|"error"|"not_implemented", "message": "..."},
            "factset": {"status": "success"|"error"|"not_implemented", "message": "..."},
            "llm": {"status": "success"|"error"|"not_implemented", "message": "..."}
        }
    """
    results = {}

    # Test Memgraph
    try:
        success, message = test_memgraph_connection(etl_manager.memgraph_client)
        results["memgraph"] = {
            "status": "success" if success else "error",
            "message": message
        }
    except Exception as e:
        results["memgraph"] = {
            "status": "error",
            "message": f"❌ Memgraph: {str(e)}"
        }

    # Test FactSet
    try:
        success, message = test_factset_connection(etl_manager.factset_client)
        results["factset"] = {
            "status": "success" if success else "error",
            "message": message
        }
    except Exception as e:
        results["factset"] = {
            "status": "error",
            "message": f"❌ FactSet: {str(e)}"
        }

    # Test LLM (placeholder)
    success, message = test_llm_connection({})
    results["llm"] = {
        "status": "not_implemented",
        "message": message
    }

    return results
