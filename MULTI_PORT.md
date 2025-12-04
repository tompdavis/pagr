# Multi-Portfolio 

PAGR should now accept multiple portfolios and use the 
database as the source of truth.  On the Portfolio seletion tab
the portfolios that are in the database should be shown, and the 
user has an option to add to this list via the Add Portfolio functionality
as before.  

In the holdings tab, the available portfolios are listed on the left hand column, and
the user can choose one or many portfolios.  When this list is changed, the main column
should update with the total positions across all portfolios.  Please add a column in the positoins
table for "Portfolio".  

The Sector and Geographic exposure underneath should have the same functionality as before, but 
return positions across all the selected portfolios, and the height of the bars should be the sum 
of the positions market value across all the selected portfolios.  

The graph view should also repsect the portfolios selection, with a view of the multiple portfolios appearing
as nodes.  When a subset of portfolios are selected, then only those nodes should appear.  

Add the portfolio selector list in a left hand column in the chat bot tab as well.  
