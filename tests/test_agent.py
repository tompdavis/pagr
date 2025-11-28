import pytest
from unittest.mock import MagicMock, patch
from pagr.agent import get_agent, search_portfolio
from langchain_core.messages import HumanMessage, AIMessage

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

def test_agent_portfolio_id_injection():
    # Test that portfolio_id is correctly injected into the system prompt
    # We can inspect the state or mock the LLM to see what it received.
    # Since we can't easily inspect the internal state of the graph during execution without a tracer,
    # we will mock ChatOllama and check the system message it received.
    
    with patch("pagr.agent.ChatOllama") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(content="Mock response", id="mock_id", tool_calls=[])
        
        agent = get_agent()
        agent.invoke({"messages": [HumanMessage(content="Hello", id="user_msg_id")], "portfolio_id": "TEST_PORTFOLIO_ID"})
        
        # Check calls to invoke
        # The argument to invoke is a list of messages. The first one should be the SystemMessage.
        call_args = mock_llm.invoke.call_args
        assert call_args is not None
        messages = call_args[0][0]
        assert len(messages) >= 2 # System + User
        system_msg = messages[0]
        assert "TEST_PORTFOLIO_ID" in system_msg.content
