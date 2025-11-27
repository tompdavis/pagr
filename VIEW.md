# Portfolio View


This aspect of the application will need to be future-proof, in that many view will need to be supported in the future.  Make sure to reflect this with the correct abstractions in the code.  

## Simplest View 
The view for phase 1 is a simple view that has the securities in a tabular format with ticker, position, market price of position,  and sector class. The market price of position is the market value of the security (fectched from the finance API) multiplied by the position size. The bottom of the table has the total market value of the portfolio, representing the sum of the market values of the positions.  Beside the table, the simple view has a stacked bar chart with the total portfolio value broken into the contribution by sector.  


