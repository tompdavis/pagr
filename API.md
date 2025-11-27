# API Specification


## Finance API 

*   Phase 1 use Yahoo Finance.  
The yahoo finance python packaage is `yfinance`. 

If a ticker is read in with a dot, it will fail, so cleaning the ticker data needs to be done by repalcing the dots with a dash
```# 1. Your list of tickers from the file
tickers = [
    "AAPL", "AEP", "AES", "ALB", "AMZN", "APO", "BRK.B", "COST", 
    "CVX", "GEHC", "GEV", "GOOGL", "LVMUY", "MDLZ", "MSFT", 
    "SBUX", "SYK", "TDG", "TEL", "TMO", "UL", "V"
]

# 2. Fix formatting (Swap '.' for '-' for Yahoo compatibility)
formatted_tickers = [t.replace('.', '-') for t in tickers]
```

To get the sector information 
`yfinance.Ticker({ticker_id_string}).info.get('Sector', 'unknown')`
The last input is the value if the sector is not known, hopefully not an issue for yahoo finance.  

To get the last night's close for a vector of tickers
`yfinance.download(formatted_tickers, period="1d", progress=False)['Close']`
