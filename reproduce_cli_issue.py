
import sys
from pagr.agent import get_agent
from langchain_core.messages import HumanMessage
from pagr.cli import PORTFOLIO_NAME

def reproduce():
    print(f"Starting CLI reproduction for portfolio: {PORTFOLIO_NAME}")
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
        
        messages = response["messages"]
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"Tool Call: {msg.tool_calls}")
            elif hasattr(msg, "content"):
                print(f"Message ({type(msg).__name__}): {msg.content}")
                
    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()
        print("-" * 50)
    print("DONE")

if __name__ == "__main__":
    reproduce()
