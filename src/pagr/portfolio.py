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
