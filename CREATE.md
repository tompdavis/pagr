# Create a Portfolio

The portfolio will be read in from a file with the extension '.pagr'.  This file will be in json format and contain a vector of positions.  Here is an example of the file 

{
  "portfolio_name": "PAGR Portfolio",
  "currency": "USD",
  "last_updated": "2024-05-21",
  "positions": [
    { "ticker": "AAPL", "quantity": 100, "book_value": 4460.50 },
    { "ticker": "AEP", "quantity": 100, "book_value": 7722.00 },
    { "ticker": "AES", "quantity": 475, "book_value": 7723.50 },
    { "ticker": "ALB", "quantity": 75, "book_value": 5618.75 },
    { "ticker": "AMZN", "quantity": 100, "book_value": 7039.82 },
    { "ticker": "APO", "quantity": 150, "book_value": 7945.50 },
    { "ticker": "BRK.B", "quantity": 35, "book_value": 7009.63 },
    { "ticker": "COST", "quantity": 20, "book_value": 6295.87 },
    { "ticker": "CVX", "quantity": 65, "book_value": 10208.25 },
    { "ticker": "GEHC", "quantity": 100, "book_value": 8164.00 },
    { "ticker": "GEV", "quantity": 50, "book_value": 7605.46 },
    { "ticker": "GOOGL", "quantity": 125, "book_value": 6530.16 },
    { "ticker": "LVMUY", "quantity": 100, "book_value": 5937.00 },
    { "ticker": "MDLZ", "quantity": 200, "book_value": 8720.00 },
    { "ticker": "MSFT", "quantity": 50, "book_value": 4543.38 },
    { "ticker": "SBUX", "quantity": 125, "book_value": 7473.93 },
    { "ticker": "SYK", "quantity": 45, "book_value": 8658.86 },
    { "ticker": "TDG", "quantity": 15, "book_value": 9567.15 },
    { "ticker": "TEL", "quantity": 75, "book_value": 9129.00 },
    { "ticker": "TMO", "quantity": 22, "book_value": 11858.73 },
    { "ticker": "UL", "quantity": 225, "book_value": 10183.13 },
    { "ticker": "V", "quantity": 60, "book_value": 7184.40 }
  ]
}

Upon reading in the portfolio, use the finance api to clean the ticker name, fetch the sector and the market price from last night's market close.  This will be used in the portfolio view.  
