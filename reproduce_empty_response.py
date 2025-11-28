
import sys
from pagr.agent import get_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from pagr.cli import PORTFOLIO_NAME

def reproduce():
    print(f"Starting empty response reproduction for portfolio: {PORTFOLIO_NAME}")
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
        
        print("\n--- Full History ---")
        for i, msg in enumerate(response["messages"]):
            print(f"[{i}] {msg}")
            sys.stdout.flush()
        print("--- End History ---\n")
        
        last_msg = response["messages"][-1]
        print(f"DEBUG: Last message type: {type(last_msg)}")
        print(f"DEBUG: Last message content: '{last_msg.content}'")
        if not last_msg.content:
            print("FAILURE: Final message content is empty.")
        else:
            print("SUCCESS: Final message has content.")
                
    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
