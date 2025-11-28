
import sys
from pagr.agent import get_agent
from langchain_core.messages import HumanMessage, AIMessage
from pagr.cli import PORTFOLIO_NAME

def reproduce():
    print(f"Starting Cypher text reproduction for portfolio: {PORTFOLIO_NAME}")
    try:
        agent = get_agent()
        
        # Simulate the user question
        question = "what is my exposure by country?"
        print(f"User: {question}")
        
        input_state = {
            "messages": [HumanMessage(content=question, id="user_msg_id")], 
            "portfolio_id": PORTFOLIO_NAME,
            "loop_step": 0
        }
        
        print(f"Invoking agent...")
        response = agent.invoke(input_state)
        
        last_msg = response["messages"][-1]
        print(f"Final response type: {type(last_msg)}")
        print(f"Final response content: {last_msg.content}")
        print(f"Final response tool_calls: {last_msg.tool_calls}")
        
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
             print("SUCCESS: Agent called a tool.")
        elif "MATCH" in last_msg.content and "RETURN" in last_msg.content:
            print("FAILURE: Agent returned Cypher text in the response content.")
        else:
            print("UNKNOWN: Agent did something else.")
                
    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
