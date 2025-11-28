import sys
from pagr.agent import get_agent, StatusCallbackHandler
from pagr.db import get_driver
from langchain_core.messages import HumanMessage, AIMessage

PORTFOLIO_NAME = "USD Odlum Portfolio"

def check_portfolio_exists(name):
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run("MATCH (p:Portfolio {name: $name}) RETURN p", name=name)
            return result.single() is not None
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
    finally:
        driver.close()

def main():
    if not check_portfolio_exists(PORTFOLIO_NAME):
        print(f"Error: Portfolio '{PORTFOLIO_NAME}' not found in database.")
        sys.exit(1)

    print(f"Chatbot CLI - querying '{PORTFOLIO_NAME}'")
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

            response = agent.invoke({"messages": history}, config={"callbacks": [handler]})
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
