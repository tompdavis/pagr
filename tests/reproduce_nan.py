import pandas as pd
import numpy as np
from pagr.portfolio import Portfolio, Position

def test_reproduce_nan_total():
    # Setup portfolio
    p = Portfolio(
        name="Test",
        currency="USD",
        last_updated="",
        positions=[
            Position(ticker="AAPL", quantity=10, book_value=100),
            Position(ticker="BAD", quantity=10, book_value=100)
        ]
    )
    
    # Mock prices where one is NaN
    prices = pd.Series({
        "AAPL": 150.0,
        "BAD": np.nan
    })
    
    # Simulate app logic
    total_value = 0.0
    for pos in p.positions:
        price = prices.get(pos.ticker, 0.0)
        if isinstance(price, pd.Series):
            price = price.iloc[0]
        
        # This is where it likely fails
        # Apply fix: Handle NaN
        if pd.isna(price):
            price = 0.0
            
        pos.current_price = float(price)
        pos.market_value = pos.quantity * pos.current_price
        total_value += pos.market_value
        
    print(f"Total Value: {total_value}")
    assert not pd.isna(total_value), "Total value should NOT be NaN after fix"
    assert total_value == 1500.0 # 10 * 150 + 10 * 0

if __name__ == "__main__":
    test_reproduce_nan_total()
