# Tabular view

PAGR is sophisticated enough now to warrant a different 
layout.  There should be the following tabs: 
 1. Settings 
 1. Portfolio selection 
 1. Holdings view 
 1. Portfolio Chat Agent

## Settings 
Each settings should have a test button that ensures the remote calls will 
work with by sending a very small test.  For the database you might as well 
get the list of portfolios in the database, at this point don't worry if 
the call comes back empty, just ensure the call worked.  For the LLM, 
send a small query to the chat agent model.  For the Factset, just 
get the stock price of FDS (and when displaying the success message, 
output the stock price!).  

Upon loading of the application, display the settings tab and make sure all
connections are valid, displaying a green icon beside each one that is 
available, and a red icon if it is not available. 

Settings sections:
 1. Memgraph 
    - host 
        - default 127.0.0.2 
    - port
        - default 7687 
    - default credentials
        - username ""
        - password ""
    - encrypted 
        - default FALSE

 1. FactSet credentials
    - Username
        - default 
    - API key
        - default 
    - base url
        - default "https://api.factset.com"
    - rate limit repeats
        - default 10 
    - timeout
        - default 30
    - max retries
        - default 3 

 1. Logging 
    - level
        - default "INFO"
        - file "logs/pagr.log"

 1. LLM (NOT IMPLEMENTED YET!)
    - LLM provider
        - default Ollama Cloud
            - url
                - default "https://ollama.com/api/generate"
            - API key
                - default "7afa688b59274e3aa76f83695ac93263.FeT5zF7eeID4Imm_I4EwAx-y"
    - Chat agent model choice
        - default gpt-oss:20b-cloud
    - Cypher model choice
        - default qwen3-coder:480b-cloud

## Portfolio Selection
Upon startup, first check the database for existing 
portfolios.  If they are there and conform to the schema
then load those in and display them in a list on this tab. 
There should be a delete portfolio button next to each
portfolio.  There should be an add portfolio button 
that prompts the user how to load a portfolio, with choices
{csv from disk, ofdb from factset account}.  The ofdb is not implemented yet
and will be in a future development effort.   


## Holdings View 
The left hand side will have a narrow column with the available portfolios 
and a selection box next to each of them with all selected by default.  

The holdings view looks like the current UI, with a choice of tabular view 
or graph view, however the views are for all positions in all the porftolios
that are selected on the left hand side. 

## Portfolio Chat Agent 

Just put at "NOT IMPLEMENTED YET" in this tab




