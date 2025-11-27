# Portfolio Analysis with GraphRag (PAGR) Overview

PAGR is a financial portfolio analysis application using a python web applet. The app automatically updates the prices of 
the equity positions present in the portfolio and displays news articles (hedlines) 
that are relevant to the portfolio.  The user can click on the news article and see a summary, as well as a brief repsonse
from an AI agent that describes the likely impact of the news on the portfolio.  

The user can also ask questions like "the fed is going to meet this month, how will my portfolio be affected by a change 
in the fed interest rate?"  Or "what would be the impact of a 10% decline in the S&P500 on my portfolio", or the classic
question "how am i exposed to GM", which requires the knowledge of bond issuance, derivative counterparties as well as 
subsidiaries, etc.  This ontology is all present in the Financial Industry Business Ontology (FIBO), which can be used
to create a knowledge graph.  


## Critical Documentation Pattern

*   Project Overview: This document, PROJECT_SPEC.md
*   APIs: API.md describes the APIs used in detail.

## Key Features

*   Create portfolio: Ability to create a portfolio from a file, a simple structure of stock ticker and quantity.  The quantity can be negative, denoting a short position.
    *   Feature described in CREATE.md
*   Trade in/out: Ability to change a position to the portfolio, defined as either selling or buying a security.
    *   Feature described in TRADE.md
*   Display portfolio: A view of the portfolio and its current market value, with a "live/static" toggle.  When static, the portfolio doesn't change its value as the market data "ticks", but uses the last night's market close values.  
*   Portfolio view: Initially, a chart showing the value of the portfolio broken down into sectors according to an abstracted sector classification.  This feature must be future-proof, meaning modular and extensible for future views.  
    *   Feature described in VIEW.md
*   News feed: A list of news items that mention any of the stocks in the portfolio, listing only the headline. 
    *   Feature described in NEWS.md
*   Scenario analysis: Enter in a list of changes in the market data (only available when the portfolio is in static mode).  
    *   Feature described in SCENARIO.md
*   Agentic querying: The user can ask an agent questions about the portfolio, like "how exposed am I to movements in the tech sector", or "what happens if the S&P500 goes down by 10%", which get translated via the agent into scenarios. Likely, 
this will have to be a LLM based routing to sub-agents, one is the scenario agent, one is the global reasoning agent, this is to be determined with future research.  
    *   Feature described in AGENTIC.md

## Architecture
PAGR will be written in python, and be accessed via a web applet, although its componenets should all have command line interfaces for individual testing.  
The components are:
*   Portfolio creation
    *   Can be created using a file, which has the .pagr extension, simply including a stock ticker and a number of shares.  TODO: provide an example file. 
    *   Can also just be created on-the-fly by executing "trades" inside of the web applet UI.
    *   The portfolio can be saved to a .pagr file structure. 
*   Portfolio viewing
    *   There can be multiple views for the portfolio, and this needs to be an extensible part of the application.  The first will just be the market value of the portfolio broken into GICS sectors, but many more can be created and added in the future.  For instance, the graph view once the graphrag componenet has been developed.  Or a sector classification heatmap.
*   Simple scenario analysis
    *   A list of stock tickers and either an absolute change in monetary value (+10 USD, -10 EUR, for example), or a relative change (+10%, -2.3%).  
    *   This will also be used internally by the scneario analysis agent.  
    *   Ability to save common scenarios in a "repository"


There are some external APIs used, and they need to be configured and have the ability to choose between different providers
1. Financial data: default is yahoo finance api 
2. LLM: default is a local install of ollama using llama3.1:8b 
3. News feed: TODO
4. Sector classification: While I would like to use GICS, it's not clear whether this can be done consistently, so using an API to do this can provide an abstraction.  

## Development Guidelines & Standards

### General Rules
The application will be written in python 3.12.  The uv package manager will be used to add packages.  Prefer simple, composable, testable functions over complex classes when possible.  Write unit tests for every feature, and if big enough, every component of the feature. 

### Testing Requirements
*   **T-1 (MUST)** Write tests for all new features and bug fixes.
*   **T-2 (SHOULD)** Run tests before committing to ensure code quality and functionality.

### Code Style
*   **C-1 (MUST)** Adhere to PEP 8 style guidelines for Python
*   **C-2 (MUST)** Use consistent docstring format (e.g., Google style).

## Workflow
*   **Planning:** For each phase, create a `PHASE_N.md` (where N is the integer denoting the phase) file first and generate an implementation plan before coding.  This will be committed, and will treated as part of the software.
*   **Committing:** Run tests before finalizing any changes.
*   **Refining:** Treat this `PROJECT_SPEC.md` as a living document and refine it constantly based on what produces the best results from the model

## Phases 

### Phase 1 
*   Read in a portfolio from a .pagr file
*   Implement the static portfolio view, using a financial API (initially yahoo finance api) to get last night's close for all the positions in the portfolio.
*   Have a simple portfolio view that is a table with security identifier, position size, market value of position, and sector classification. 

### Phase 2
*   Have a button to "Trade In/Out" 

### Phase 3
*   When the portfolio is read from a file, create a GraphRAG database for queries about the portfolio

### Phase 4 
*   Implement the live view of the portfolio where the securities in the portfolio update their prices as the market ticks.

### Phase 5
*   Have a news feed which queries a news API for news items that reference the entities in the portfolio, as well as the sectors in the portfolio. 

### Pase 6
*  Create the scenario analysis  

### Future Phases
*   Foreign exchange handling 
*   Book value for calculating returns 
*   Trade blotter
*   Cash management
