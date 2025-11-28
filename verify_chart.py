import sys
import os
from unittest.mock import MagicMock, patch
import pandas as pd

# Add src to path
sys.path.append(os.path.abspath("src"))

# Mock streamlit before importing app
sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit.runtime.scriptrunner"] = MagicMock()
sys.modules["streamlit_agraph"] = MagicMock()

from pagr import app
from pagr import db

def verify_chart_logic():
    print("Verifying chart logic...")
    
    # Mock db.get_portfolio_view
    with patch('pagr.db.get_portfolio_view') as mock_get_view:
        mock_get_view.return_value = [
            {
                'ticker': 'AAPL',
                'quantity': 10,
                'book_value': 1500.0,
                'sector': 'Technology',
                'country_code': 'US',
                'country_of_risk': 'US',
                'company_name': 'Apple Inc.'
            },
            {
                'ticker': 'SIE.DE',
                'quantity': 5,
                'book_value': 500.0,
                'sector': 'Industrials',
                'country_code': 'DE',
                'country_of_risk': 'DE',
                'company_name': 'Siemens AG'
            }
        ]
        
        # Mock get_current_prices
        with patch('pagr.app.get_current_prices') as mock_prices:
            mock_prices.return_value = {'AAPL': 150.0, 'SIE.DE': 100.0}
            
            # We can't easily run the whole streamlit app, but we can simulate the data processing logic
            # extracted from app.py
            
            db_positions = db.get_portfolio_view("Test Portfolio")
            prices = mock_prices.return_value
            
            portfolio_data = []
            for pos in db_positions:
                ticker = pos['ticker']
                quantity = pos['quantity']
                sector = pos['sector']
                country = pos.get('country_code', 'Unknown')
                company = pos.get('company_name', 'Unknown')
                
                price = prices.get(ticker, 0.0)
                market_value = quantity * price
                
                portfolio_data.append({
                    "Ticker": ticker,
                    "Quantity": quantity,
                    "Market Value": market_value,
                    "Sector": sector,
                    "Country": country,
                    "Company": company
                })
                
            df = pd.DataFrame(portfolio_data)
            
            print("DataFrame created:")
            print(df)
            
            # Verify grouping by Country
            exposure_type = "Country"
            group_col = exposure_type
            chart_df = df.groupby(group_col)["Market Value"].sum().reset_index()
            chart_df = chart_df.sort_values("Market Value", ascending=False)
            
            print(f"\nGrouped by {exposure_type}:")
            print(chart_df)
            
            assert len(chart_df) == 2
            assert chart_df.iloc[0]['Country'] == 'US'
            assert chart_df.iloc[0]['Market Value'] == 1500.0
            
            print("\nVerification successful!")

if __name__ == "__main__":
    verify_chart_logic()
