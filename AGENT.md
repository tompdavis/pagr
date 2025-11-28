# Add a Chatbot Agent to Interact with the Portfolio


The purpose of this feature is to allow the user to interact with the portfolio
via a chatbot powered by an LLM.  

Initially this will be a local LLM powered by ollama on localhost port 11434 (please test this,
it's in a docker container, so the gateway might be `host.docker.internal`).

The chatbot agent will have access to a tool to perform graph search on the portfolio, which
is stored in a memgraph database on localhost port 7687.

## Chatbot Agent Setup 
The chatbot is a financial analyts, concerned primarily with the sources of risk in the 
client's portfolio.  Therefore the system prompt must be such that it will focus on this, 
and never hallucinate, it will prefer asking the client for clarification rather than 
guess.  It will use a graph search to turn the client questions into results from the 
portfolio.  

The agent should be optimized for the following set of questions:
- "What is my exposure to a given sector?"
- "What is my biggest exposure by sector?" 
- "How am I exposed to an individual stock?"
- "How am I exposed to a coutry or region?"


## Graph Search Tool 

The chatbot will take the clients request and determine which aspects of the portfolio to 
query for.  The most common are 
*   Individual stocks (such as AAPL)
*   Sectors (such as healthcare)
*   Country of risk (such as the United States)
*   Regions (such as Europe)

The database is memgraph, and therefore can be queried using cypher.  

The resulting set of positions is returned to the chatbot agent.  

The test question for the chatbot is "How am I exposed to the technology sector?"


## The UI 
The chat bot will be launched by a button on the left hand side "Portfolio Chat", which 
creates a pane underneath the portfolio view for the interaction.  The pane is split in two
on the left hand side is the chat, and on the right hand side is the logging.  There is a button
to hide the chat, but this does not kill the chatbot or the context.  However there is a button 
that is called "Reset context" which restars the chatbot.  

Sometimes the chatbot returns a message with cypher text contained within it.  Can you catch
this case, and when it happens, output to the user "I'm sorry, I can't figure out your request, please see
the logs", and show the full error in the log.  
