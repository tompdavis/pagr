import os
from typing import Any, Dict, List, Literal, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.callbacks import BaseCallbackHandler
from pagr.db import get_driver

# Configuration
MODEL_NAME = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# --- STATE ---
class AgentState(Dict):
    messages: List[BaseMessage]

# --- LOGGING ---
class StatusCallbackHandler(BaseCallbackHandler):
    def __init__(self, log_callback):
        self.log_callback = log_callback

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        self.log_callback("thinking")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        if serialized.get("name") == "search_portfolio":
            self.log_callback("examining portfolio (graph search)")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        self.log_callback("formulating response")

# --- TOOLS ---
@tool
def search_portfolio(query: str) -> str:
    """
    Search the portfolio database using a Cypher query.
    The database has the following schema:
    - (:Portfolio)-[:CONTAINS]->(:Position)-[:IS_INVESTED_IN]->(:Company)
    - Position properties: ticker, qty, book_val
    - Company properties: name, sector, lei, ticker
    
    You should write a Cypher query to answer the user's question.
    """
    driver = get_driver()
    try:
        with driver.session() as session:
            # We use read transaction for safety
            result = session.run(query)
            data = [record.data() for record in result]
            return str(data)
    except Exception as e:
        return f"Error executing query: {e}"
    finally:
        driver.close()

# --- NODES ---
def agent_node(state: AgentState):
    messages = state["messages"]
    model = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0)
    model = model.bind_tools([search_portfolio])
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"

# --- GRAPH DEFINITION ---
def get_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode([search_portfolio]))
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
