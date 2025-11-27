import json
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

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
    def from_file(cls, file_path: str | Path) -> 'Portfolio':
        """Loads a portfolio from a .pagr (JSON) file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Portfolio file not found: {file_path}")
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        positions = []
        for pos_data in data.get('positions', []):
            positions.append(Position(
                ticker=pos_data['ticker'],
                quantity=pos_data['quantity'],
                book_value=pos_data['book_value']
            ))
            
        return cls(
            name=data.get('portfolio_name', 'Unknown Portfolio'),
            currency=data.get('currency', 'USD'),
            last_updated=data.get('last_updated', ''),
            positions=positions
        )

    def get_tickers(self) -> List[str]:
        """Returns a list of tickers in the portfolio."""
        return [p.ticker for p in self.positions]

    def add_position(self, ticker: str, quantity: float):
        """
        Adds or updates a position in the portfolio.
        If quantity becomes 0, the position is removed.
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
