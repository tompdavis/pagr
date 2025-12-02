"""Portfolio and position data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Position(BaseModel):
    """Individual position in a portfolio."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL-US",
                "quantity": 100,
                "book_value": 19000.00,
                "security_type": "Common Stock",
                "isin": "US0378331005",
                "weight": 25.5,
            }
        }
    )

    ticker: str = Field(..., description="Security ticker (e.g., AAPL-US)")
    quantity: float = Field(..., description="Number of shares/units", gt=0)
    book_value: float = Field(..., description="Book value (cost basis) in USD", ge=0)
    security_type: str = Field(default="Common Stock", description="Type of security")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    cusip: Optional[str] = Field(default=None, description="CUSIP identifier")
    market_value: Optional[float] = Field(default=None, description="Current market value in USD (fetched separately)")
    purchase_date: Optional[str] = Field(default=None, description="Purchase date (ISO format)")
    weight: Optional[float] = Field(default=None, description="Portfolio weight (%)")


class Portfolio(BaseModel):
    """A portfolio containing multiple positions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sample Portfolio",
                "created_at": "2024-01-15T10:30:00",
                "positions": [
                    {
                        "ticker": "AAPL-US",
                        "quantity": 100,
                        "book_value": 19000.00,
                        "security_type": "Common Stock",
                    },
                    {
                        "ticker": "MSFT-US",
                        "quantity": 50,
                        "book_value": 21000.00,
                        "security_type": "Common Stock",
                    },
                ],
                "total_value": 40000.00,
            }
        }
    )

    name: str = Field(default="Portfolio", description="Portfolio name")
    created_at: Optional[str] = Field(default=None, description="Portfolio creation timestamp (ISO format)")
    positions: list[Position] = Field(default=[], description="List of positions")
    total_value: Optional[float] = Field(default=None, description="Total portfolio value")

    def calculate_weights(self) -> None:
        """Calculate portfolio weights.

        Uses market_value if available for positions, otherwise falls back to book_value.
        """
        if not self.positions:
            self.total_value = 0
            return

        # Check if we should use market value (if at least one position has it)
        # Ideally we want all, but we'll sum what we have
        has_market_value = any(p.market_value is not None for p in self.positions)

        if has_market_value:
            # Use market value where available, fallback to book_value?
            # Mixing them is dangerous. Let's assume if we have market values we use them.
            # If a position is missing market value, it contributes 0 to total market value.
            self.total_value = sum((p.market_value or 0.0) for p in self.positions)
            
            if self.total_value > 0:
                for position in self.positions:
                    val = position.market_value or 0.0
                    position.weight = (val / self.total_value) * 100
            else:
                for position in self.positions:
                    position.weight = 0
        else:
            # Fallback to book value
            self.total_value = sum(p.book_value for p in self.positions)

            if self.total_value > 0:
                for position in self.positions:
                    position.weight = (position.book_value / self.total_value) * 100
            else:
                for position in self.positions:
                    position.weight = 0

    def add_position(self, position: Position) -> None:
        """Add a position to the portfolio.

        Args:
            position: Position to add
        """
        self.positions.append(position)
        self.calculate_weights()

    def remove_position(self, ticker: str) -> bool:
        """Remove a position by ticker.

        Args:
            ticker: Ticker to remove

        Returns:
            True if position was removed, False if not found
        """
        original_length = len(self.positions)
        self.positions = [p for p in self.positions if p.ticker != ticker]
        removed = len(self.positions) < original_length

        if removed:
            self.calculate_weights()

        return removed

    def get_position(self, ticker: str) -> Optional[Position]:
        """Get a position by ticker.

        Args:
            ticker: Ticker to find

        Returns:
            Position if found, None otherwise
        """
        for position in self.positions:
            if position.ticker == ticker:
                return position
        return None
