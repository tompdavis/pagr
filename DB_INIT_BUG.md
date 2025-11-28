#  Database initialization


Whenever the CLI or the application first loads, first check to see if a portfolio of the same 
name exists in the database.  If it does, load the portfolio from the database, and do not read the
data in from the file.  


For the web applet, focus on speed, or at least the appearance of speed.  Pre-load the portfolio 
and spin up the chatbot agent before launching the website, otherwise the user is waiting for 
everything to load.  

The data item "book value" is currently misinterpreted by the code.  It is not the current market 
value of the security, it is the cost of initially purchasing that position.  Upon loading the 
portfolio for the first time, add a new field that is the current market price, as fecthed 
from yahoo finance (which works in the simple table view).  

Record two more TODOs, one is add a column for the return of the portfolio based on the book value 
(representing the initial cost of the position) versus today's market value.  The second is 
to change the behaviour of the TRADE IN/OUT to respect the new definition of the book value.  
