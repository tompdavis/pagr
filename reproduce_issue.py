
import sys
from pagr.agent import get_agent
from langchain_core.messages import HumanMessage, AIMessage
from unittest.mock import MagicMock, patch

def reproduce():
    print("Starting reproduction...")
    try:
        with patch("pagr.agent.ChatOllama") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.return_value = AIMessage(content="Mock response", id="mock_id", tool_calls=[])
            
            agent = get_agent()
            print("Agent created.")
            
            input_state = {
                "messages": [HumanMessage(content="Hello", id="user_msg_id")], 
                "portfolio_id": "TEST_PORTFOLIO_ID",
                "loop_step": 0
            }
            print(f"Invoking agent with state: {input_state}")
            
            response = agent.invoke(input_state)
            print("Invocation successful.")
            print(response)
            
    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
