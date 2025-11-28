import os
from typing import Any, Dict, List, Literal, Union, TypedDict
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
MAX_RETRIES = 5

# --- STATE ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    # Track how many times we've looped
    loop_step: int
    # Portfolio ID context
    portfolio_id: str

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
    Executes a read-only Cypher query against the portfolio graph database.

    Use this tool to retrieve specific data points, aggregations, or structural relationships regarding the portfolio, positions, and companies.

    Args:
        query (str): A valid Neo4j Cypher query string. 
                    MUST initiate with 'MATCH'. 
                    MUST NOT contain write operations (CREATE, DELETE, SET).
                    MUST filter by the specific Portfolio ID in context.

    Returns:
        List[Dict]: A list of dictionaries representing the records returned by the database. Returns an empty list if no matches found.
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
    portfolio_id = state.get("portfolio_id", "UNKNOWN_PORTFOLIO")

    # 1. Define a robust System Prompt with Schema and Examples
    # This acts as the "Context" for the model so it knows HOW to write the Cypher.
    system_prompt_content = """
You are an expert Financial Analyst Agent. Your role is to query a Neo4j Graph Database to answer questions about a SPECIFIC portfolio.

### CURRENT CONTEXT
You are currently analyzing the following Portfolio:
**Portfolio ID:** `{current_portfolio_id}` 
*(Note: You must inject this ID programmatically into the prompt at runtime)*

### DATABASE SCHEMA (Strict Type Definitions)
Nodes:
- :Portfolio
    - name (String)
- :Position 
    - ticker (String)
    - qty (Float)
    - book_val (Float) - Represents the current market value in USD.
- :Company 
    - name (String)
    - sector (String) - E.g., 'Technology', 'Healthcare'
    - lei (String)
    - ticker (String)
    - currency (String)
    - country (String)

Relationships:
- (:Portfolio)-[:CONTAINS]->(:Position)
- (:Position)-[:IS_INVESTED_IN]->(:Company)

### CRITICAL RULES
1. **Context Isolation:** You must ALWAYS filter your query by the `Portfolio ID` provided in the Context. Never aggregate data across all portfolios.
2. **Read-Only:** You are strictly forbidden from using CREATE, MERGE, DELETE, SET, or DETACH. Use only MATCH, WITH, WHERE, RETURN, ORDER BY, LIMIT.
3. **Implicit Grouping:** DO NOT use `GROUP BY`. Cypher groups automatically by non-aggregated fields in RETURN.
4. **Data Integrity:** If a user asks for "Exposure," calculate `sum(p.book_val)`.
4. **Formatting:** Summarize the findings based on the tool output. Provide a clear and concise answer to the user's question.
5. **Tool Usage:** You MUST use the `search_portfolio` tool to execute Cypher. **DO NOT** output Cypher code in markdown blocks. **DO NOT** just write the query in text. You MUST call the tool.

### REASONING PROCESS
Before calling the tool, think step-by-step:
1. Identify the user's intent (e.g., Aggregation, Filtering, Lookup).
2. Identify the necessary nodes and relationships.
3. Formulate the Cypher query ensuring the `{current_portfolio_id}` is included in the MATCH or WHERE clause.

### EXAMPLES

User: "What is my exposure by country?"
Thought: The user wants to sum book_val grouped by company country for the current portfolio ID '{current_portfolio_id}'.
Tool Call:
MATCH (p:Portfolio {name: '{current_portfolio_id}'})-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company)
RETURN c.country as country, sum(pos.book_val) as total_exposure
ORDER BY total_exposure DESC

User: "List all my positions in Apple."
Thought: The user is looking for a specific ticker or company name within this portfolio.
Tool Call:
MATCH (p:Portfolio {name: '{current_portfolio_id}'})-[:CONTAINS]->(pos:Position)-[:IS_INVESTED_IN]->(c:Company)
WHERE c.name CONTAINS 'Apple' OR c.ticker = 'AAPL'
RETURN c.name, pos.qty, pos.book_val

### ERROR HANDLING
### ERROR HANDLING
If the tool returns a CypherSyntaxError or any other error:
1. Read the error message to locate the syntax fault.
2. Adjust the query (check relationship directions and property names).
4. **DO NOT** explain the error to the user. **DO NOT** ask for clarification. **ALWAYS** retry with a corrected query.
5. **RETRY INSTRUCTION:** To retry, you MUST generate a new `search_portfolio` tool call. Do not just think about it. Call the tool.

### CRITICAL INSTRUCTION
You MUST use the `search_portfolio` tool to execute Cypher. 
**DO NOT** output Cypher code in markdown blocks. 
**DO NOT** just write the query in text. 
**YOU MUST CALL THE TOOL.**
    """

    # 2. Convert to SystemMessage
    # Inject the portfolio ID
    # Use replace instead of format because the prompt contains Cypher syntax with curly braces
    formatted_system_prompt = system_prompt_content.replace("{current_portfolio_id}", portfolio_id)
    system_message = SystemMessage(content=formatted_system_prompt)

    # 3. Prepend the system message to the message history
    # This ensures the model sees instructions first, then the user's question.
    messages_with_system = [system_message] + messages

    model = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0)
    model = model.bind_tools([search_portfolio])
    
    # 4. Invoke with the updated list
    response = model.invoke(messages_with_system)
    
    output_messages = [response]
    
    # 5. Validation Logic
    if isinstance(response, AIMessage) and not response.tool_calls:
        content = response.content
        if "MATCH" in content and "RETURN" in content:
            # The model outputted Cypher text instead of calling the tool
            output_messages.append(HumanMessage(content="ERROR: You outputted raw Cypher text. You MUST use the `search_portfolio` tool to execute the query. Please try again and CALL THE TOOL."))
        elif not content.strip():
             # The model outputted nothing and no tool calls
            output_messages.append(HumanMessage(content="ERROR: You outputted an empty message. You MUST use the `search_portfolio` tool to execute the query. Please try again and CALL THE TOOL."))

    return {
            "messages": output_messages,
            "loop_step": current_step + 1
            }

def should_continue(state: AgentState) -> Literal["tools", "agent", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    current_step = state.get("loop_step", 0)
    
    if isinstance(last_message, HumanMessage) and "ERROR" in last_message.content:
        # We just added an error message in the validation node, so loop back to agent
        return "agent"

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
