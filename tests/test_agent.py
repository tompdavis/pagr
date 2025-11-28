import pytest
from unittest.mock import MagicMock, patch
from pagr.agent import get_agent, search_portfolio
from langchain_core.messages import HumanMessage

@pytest.fixture
def mock_driver():
    with patch("pagr.agent.get_driver") as mock:
        yield mock

def test_agent_initialization():
    agent = get_agent()
    assert agent is not None

def test_search_portfolio_tool(mock_driver):
    # Mock DB session and result
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
    mock_result = MagicMock()
    mock_session.run.return_value = mock_result
    mock_result.__iter__.return_value = [
        MagicMock(data=lambda: {"name": "Apple", "sector": "Technology"})
    ]
    
    result = search_portfolio.invoke("MATCH (c:Company) RETURN c")
    assert "Apple" in result
    assert "Technology" in result

@pytest.mark.skip(reason="Requires running Ollama")
def test_agent_integration():
    # This test requires Ollama to be running
    agent = get_agent()
    response = agent.invoke({"messages": [HumanMessage(content="Hello")]})
    assert response["messages"][-1].content
