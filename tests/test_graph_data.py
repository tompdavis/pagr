import pytest
from unittest.mock import MagicMock, patch
from pagr import db

@patch('pagr.db.get_driver')
def test_get_graph_data(mock_get_driver):
    # Mock the driver and session
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_get_driver.return_value = mock_driver
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock data for Portfolio Node
    mock_portfolio_result = [
        {'p': {'name': 'TestPortfolio'}}
    ]
    
    # Mock data for Positions
    mock_positions_result = [
        {'ticker': 'AAPL', 'qty': 10, 'book_val': 1500},
        {'ticker': 'GOOGL', 'qty': 5, 'book_val': 2000}
    ]
    
    # Mock data for Companies
    mock_companies_result = [
        {'ticker': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'lei': 'LEI123', 'cid': 'ID_AAPL'},
        {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Communication', 'lei': 'LEI456', 'cid': 'ID_GOOGL'}
    ]

    def create_mock_record(data_dict):
        m = MagicMock()
        m.data.return_value = data_dict
        m.__getitem__.side_effect = lambda k: data_dict[k]
        return m

    # Configure side_effect for session.run to return different results for different queries
    def side_effect(query, **kwargs):
        # Normalize whitespace for easier matching if needed, or just match unique parts
        if "RETURN p" in query and "pos" not in query:
            return [create_mock_record(r) for r in mock_portfolio_result]
        elif "c.name" in query:
            return [create_mock_record(r) for r in mock_companies_result]
        elif "pos.qty" in query:
            return [create_mock_record(r) for r in mock_positions_result]
        return []

    mock_session.run.side_effect = side_effect

    nodes, edges = db.get_graph_data("TestPortfolio")

    # Verify Nodes
    # 1 Portfolio + 2 Positions + 2 Companies = 5 Nodes
    assert len(nodes) == 5
    
    # Check Portfolio Node
    assert nodes[0]['id'] == "PORTFOLIO_TestPortfolio"
    assert nodes[0]['type'] == "Portfolio"
    
    # Check Position Nodes
    pos_nodes = [n for n in nodes if n['type'] == "Position"]
    assert len(pos_nodes) == 2
    assert any(n['id'] == "POS_AAPL" for n in pos_nodes)
    
    # Check Company Nodes
    comp_nodes = [n for n in nodes if n['type'] == "Company"]
    assert len(comp_nodes) == 2
    assert any(n['id'] == "ID_AAPL" for n in comp_nodes)

    # Verify Edges
    # 2 CONTAINS + 2 INVESTED_IN = 4 Edges
    assert len(edges) == 4
    
    contains_edges = [e for e in edges if e['label'] == "CONTAINS"]
    assert len(contains_edges) == 2
    
    invested_edges = [e for e in edges if e['label'] == "INVESTED_IN"]
    assert len(invested_edges) == 2
