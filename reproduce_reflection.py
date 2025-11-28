
import sys
from pagr.agent import get_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from unittest.mock import MagicMock, patch

def reproduce():
    print("Starting reflection reproduction...")
    try:
        # Mock the LLM to simulate the failure scenario
        # 1. First call: Generates a bad Cypher query
        # 2. Tool execution: Returns an error
        # 3. Second call (Reflection): Should retry, but currently explains the error
        
        with patch("pagr.agent.ChatOllama") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            mock_llm.bind_tools.return_value = mock_llm
            
            # Define the sequence of responses
            # Response 1: Tool call with bad query
            bad_tool_call = AIMessage(
                content="", 
                tool_calls=[{"name": "search_portfolio", "args": {"query": "BAD QUERY"}, "id": "call_1"}]
            )
            
            # Response 2: Retry with corrected query (The Fix)
            retry_tool_call = AIMessage(
                content="", 
                tool_calls=[{"name": "search_portfolio", "args": {"query": "CORRECTED QUERY"}, "id": "call_2"}]
            )
            
            # Response 3: Final success (after retry)
            final_success = AIMessage(content="Here is the exposure by country: ...")
            
            mock_llm.invoke.side_effect = [bad_tool_call, retry_tool_call, final_success]
            
            # Mock the tool execution to return an error
            with patch("pagr.agent.search_portfolio") as mock_tool:
                # We need to mock the tool node execution or just let the graph run
                # Since we are mocking the LLM, we also need to ensure the tool node runs
                # But wait, we are using the real graph, so we should mock the tool function itself
                # The tool function is decorated, so we patch the underlying function or the tool in the module
                pass

            # Actually, let's just run the agent and see what happens with a mocked LLM
            # We need to mock the DB driver to return an error when the tool is called
            with patch("pagr.agent.get_driver") as mock_driver:
                mock_session = MagicMock()
                mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
                mock_session.run.side_effect = Exception("CypherSyntaxError: Invalid syntax")
                
                agent = get_agent()
                print("Agent created.")
                
                input_state = {
                    "messages": [HumanMessage(content="What is my exposure by country?", id="user_msg_id")], 
                    "portfolio_id": "TEST_PORTFOLIO_ID",
                    "loop_step": 0
                }
                
                print(f"Invoking agent...")
                response = agent.invoke(input_state)
                
                last_msg = response["messages"][-1]
                print(f"Final response type: {type(last_msg)}")
                print(f"Final response content: {last_msg.content}")
                
                # Verification logic
                # Check if there was a second tool call in the history
                messages = response['messages']
                tool_calls_count = 0
                for msg in messages:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        tool_calls_count += 1
                
                print(f"Total tool calls found: {tool_calls_count}")
                
                if tool_calls_count >= 2:
                    print("SUCCESS: Agent retried with a new tool call!")
                else:
                    print("FAILURE: Agent did not retry.")

    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
