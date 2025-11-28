import sys
from pagr.agent import get_agent, StatusCallbackHandler
from pagr.db import get_driver
from langchain_core.messages import HumanMessage, AIMessage

from pagr.portfolio import Portfolio
from pathlib import Path

PORTFOLIO_NAME = "USD Odlum Portfolio"
DEFAULT_FILE = Path("default_portfolio.pagr")

def main():
    print(f"Chatbot CLI - querying '{PORTFOLIO_NAME}'")
    
    try:
        # Load portfolio (checks DB first, then file)
        portfolio = Portfolio.load(PORTFOLIO_NAME, DEFAULT_FILE)
        print(f"Successfully loaded portfolio: {portfolio.name}")
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        sys.exit(1)

    print("Type 'exit' or 'quit' to stop.")

    agent = get_agent()
    history = []

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue

            history.append(HumanMessage(content=user_input))

            print("\n--- Logs ---")
            def log_callback(msg):
                print(f"[Log] {msg}")

            handler = StatusCallbackHandler(log_callback)

            response = agent.invoke({"messages": history, "portfolio_id": PORTFOLIO_NAME}, config={"callbacks": [handler]})
            ai_msg = response["messages"][-1]
            history.append(ai_msg)
            
            print("--- End Logs ---\n")
            print(f"Agent: {ai_msg.content}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
