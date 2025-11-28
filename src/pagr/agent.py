import os
from typing import Any, Dict, List, Literal, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import SystemMessage
from pagr.db import get_driver
from typing import Annotated
import operator

# Configuration
MODEL_NAME = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"
MAX_RETRIES = 3

# --- STATE ---
class AgentState(Dict):
    messages: Annotated[List[BaseMessage], operator.add]
    # Track how many times we've looped
    loop_step: int

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
    current_step = state.get("loop_step", 0)

    # 1. Define a robust System Prompt with Schema and Examples
    # This acts as the "Context" for the model so it knows HOW to write the Cypher.
    system_prompt_content = """
    You are a financial analyst agent. Your goal is to answer questions about a portfolio using a graph database.
    
    You have access to a tool called 'search_portfolio' which executes Cypher queries.
    You must generate valid Cypher to answer the user's question.
    
    ### DATABASE SCHEMA
    Nodes:
    - :Portfolio (id)
    - :Position (ticker, qty, book_val)
    - :Company (name, sector, lei, ticker, currency, country)
    
    Relationships:
    - (:Portfolio)-[:CONTAINS]->(:Position)
    - (:Position)-[:IS_INVESTED_IN]->(:Company)
    
    ### EXAMPLES (Use these patterns)
    
    User: "What is my biggest sector exposure?"
    Query: MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company) 
           RETURN c.sector as sector, sum(pos.book_val) as total_value 
           ORDER BY total_value DESC LIMIT 1
    
    User: "List all my positions in the Technology sector"
    Query: MATCH (p:Portfolio)-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company)
           WHERE c.sector = 'Technology'
           RETURN c.name, pos.qty, pos.book_val
    
    ### INSTRUCTIONS
    1. Always use the 'search_portfolio' tool to get data.
    2. Do not make up data. If the query returns empty, tell the user.
    3. Return the exact Cypher query string in the tool call.

    ### ERROR HANDLING
    If the search tool returns an error (e.g., "CypherSyntaxError"), analyze the error message carefully.
    1. Identify which part of the query failed.
    2. Rewrite the query to fix the syntax.
    3. Call the tool again with the corrected query.
    DO NOT apologize. Just fix the query and try again.
    """

    # 2. Convert to SystemMessage
    system_message = SystemMessage(content=system_prompt_content)

    # 3. Prepend the system message to the message history
    # This ensures the model sees instructions first, then the user's question.
    messages_with_system = [system_message] + messages

    model = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0)
    model = model.bind_tools([search_portfolio])
    
    # 4. Invoke with the updated list
    response = model.invoke(messages_with_system)
    
    return {
            "messages": [response],
            "loop_step": current_step + 1
            }



def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    current_step = state.get("loop_step", 0)

    if not last_message.tool_calls:
        return "__end__"

    if current_step >= MAX_RETRIES:
        return "__end__"

    return "tools"

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
