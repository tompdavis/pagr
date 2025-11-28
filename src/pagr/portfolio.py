import json
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from pagr.market_data import get_current_prices
import pandas as pd

@dataclass
class Position:
    ticker: str
    quantity: float
    book_value: float
    sector: str = "Unknown"
    current_price: float = 0.0
    market_value: float = 0.0

@dataclass
class Portfolio:
    name: str
    currency: str
    last_updated: str
    positions: List[Position]

    @classmethod
    def load(cls, name: str, file_path: str | Path) -> 'Portfolio':
        """
        Loads the portfolio. Checks the database first.
        If found in DB, loads from there.
        If not found, loads from file and syncs to DB.
        """
        from pagr import db
        
        if db.check_portfolio_exists(name):
            print(f"Loading portfolio '{name}' from database...")
            portfolio = db.get_portfolio(name)
            # We still need to fetch current prices for the loaded portfolio
            portfolio.update_prices()
            return portfolio
        else:
            print(f"Portfolio '{name}' not found in database. Loading from file...")
            portfolio = cls.from_file(file_path)
            # Sync to DB
            portfolio.to_db()
            return portfolio

    @classmethod
    def from_file(cls, file_path: str | Path) -> 'Portfolio':
        """Loads a portfolio from a .pagr (JSON) file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Portfolio file not found: {file_path}")
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        positions = []
        tickers = []
        raw_positions = data.get('positions', [])
        
        for pos_data in raw_positions:
            tickers.append(pos_data['ticker'])

        # Fetch current prices
        prices = get_current_prices(tickers)

        for pos_data in raw_positions:
            ticker = pos_data['ticker']
            quantity = pos_data['quantity']
            book_value = pos_data['book_value']
            
            # Get current price
            price = prices.get(ticker, 0.0)
            if isinstance(price, pd.Series):
                price = price.iloc[0]
            if pd.isna(price):
                price = 0.0
            current_price = float(price)
            
            positions.append(Position(
                ticker=ticker,
                quantity=quantity,
                book_value=book_value,
                current_price=current_price,
                market_value=quantity * current_price
            ))
            
        return cls(
            name=data.get('portfolio_name', 'Unknown Portfolio'),
            currency=data.get('currency', 'USD'),
            last_updated=data.get('last_updated', ''),
            positions=positions
        )

    def update_prices(self):
        """Updates current prices and market values for all positions."""
        tickers = self.get_tickers()
        prices = get_current_prices(tickers)
        
        for pos in self.positions:
            price = prices.get(pos.ticker, 0.0)
            if isinstance(price, pd.Series):
                price = price.iloc[0]
            if pd.isna(price):
                price = 0.0
            pos.current_price = float(price)
            pos.market_value = pos.quantity * pos.current_price

    def get_tickers(self) -> List[str]:
        """Returns a list of tickers in the portfolio."""
        return [p.ticker for p in self.positions]

    def add_position(self, ticker: str, quantity: float):
        """
        Adds or updates a position in the portfolio.
        If quantity becomes 0, the position is removed.
        
        TODO: Change the behaviour of the TRADE IN/OUT to respect the new definition of the book value.
        Currently, this does not correctly handle book value updates (weighted average cost).
        """
        # Check if position exists
        existing_pos = next((p for p in self.positions if p.ticker == ticker), None)
        
        if existing_pos:
            existing_pos.quantity += quantity
            # Remove if quantity is 0 (or very close to 0 to handle float precision)
            if abs(existing_pos.quantity) < 1e-9:
                self.positions.remove(existing_pos)
        else:
            if abs(quantity) > 1e-9:
                # Add new position
                # Note: book_value is not updated correctly here as we don't have price info
                # For now, we'll just set it to 0 or keep it as is. 
                # Ideally we'd pass price to this method or update it later.
                self.positions.append(Position(
                    ticker=ticker,
                    quantity=quantity,
                    book_value=0.0 # Placeholder
                ))

    def save(self, file_path: str | Path):
        """Saves the portfolio to a .pagr (JSON) file."""
        data = {
            "portfolio_name": self.name,
            "currency": self.currency,
            "last_updated": self.last_updated,
            "positions": [
                {
                    "ticker": p.ticker,
                    "quantity": p.quantity,
                    "book_value": p.book_value
                }
                for p in self.positions
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def to_db(self):
        """Persists the portfolio to the Memgraph database."""
        from pagr import db
        db.load_portfolio(self)

# TODO: Add a column for the return of the portfolio based on the book value (representing the initial cost of the position) versus today's market value.
