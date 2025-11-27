# Trade In and Out of a Position 


PAGR will allow the user to ammend their portfolio by trading, with a button marked "Trade In/Out".  This prompts the user to enter the security ID and the number of securities to trade.  The number can be positive or negative, positive reprenting buying the security and adding more of it to the portfolio, and negative means selling it and reduces the position in the portfolio.  A negative portfolio position is OK, this just means the portfolio is short that number of shares.  Different APIs require different conventions for tickers, for instance google finance API uses a dot whereas yahoo finance uses a dash for denoting different classes of shares.  For example Berkshire Hathaway Class B shares would be BRK-B in Yahoo finance but BRK.B in google finance.  This quirk of the API should be detailed in the API.md document.  

When the trade is entered, the ticker should be validated as correctly identifying a share via the finance api.  


### Future Functionality 
*   When checking the ticker, if not found, suggest fixes
*   When entering ticker, use a type of search that can automatically find the ticker 
