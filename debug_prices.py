
import logging
import requests
import json
from pathlib import Path

def debug_price_fetch():
    # Read credentials
    creds = {}
    with open("fds-api.key") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                creds[k] = v.strip('"\'')
    
    username = creds["FDS_USERNAME"]
    api_key = creds["FDS_API_KEY"]
    
    url = "https://api.factset.com/content/factset-global-prices/v1/prices"
    
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    payload = {
        "ids": ["AAPL-US", "MSFT-US"],
        "frequency": "D",
        "startDate": start_date,
        "endDate": end_date
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=(username, api_key),
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_price_fetch()
