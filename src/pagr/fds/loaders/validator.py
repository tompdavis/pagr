"""Validation logic for portfolio data."""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class PositionValidator:
    """Validates portfolio position data."""

    # Required columns for a position
    # Note: Either 'book_value' OR 'market_value' is required (book_value preferred)
    REQUIRED_COLUMNS = {"ticker", "quantity"}
    VALUE_COLUMNS = {"book_value", "market_value"}  # At least one required

    # Optional columns
    OPTIONAL_COLUMNS = {"security_type", "isin", "cusip", "purchase_date"}

    # All valid columns
    VALID_COLUMNS = REQUIRED_COLUMNS | VALUE_COLUMNS | OPTIONAL_COLUMNS

    @classmethod
    def validate_headers(cls, headers: List[str]) -> None:
        """Validate CSV headers.

        Args:
            headers: List of column headers

        Raises:
            ValidationError: If required columns missing
        """
        # Normalize headers: lowercase, strip whitespace, replace spaces with underscores
        # Handle multiple types of whitespace (spaces, tabs, etc.)
        headers_set = set()
        for h in headers:
            if h:  # Skip empty strings
                normalized = h.strip().lower().replace(" ", "_").replace("\t", "_")
                headers_set.add(normalized)

        logger.debug(f"Validated headers_set: {sorted(headers_set)}")
        logger.debug(f"Required columns: {sorted(cls.REQUIRED_COLUMNS)}")
        logger.debug(f"Value columns (book_value OR market_value): {sorted(cls.VALUE_COLUMNS)}")

        # Check required columns (ticker, quantity)
        missing = cls.REQUIRED_COLUMNS - headers_set

        if missing:
            logger.error(f"Missing required columns: {missing}, Got: {headers_set}")
            raise ValidationError(
                f"Missing required columns: {', '.join(sorted(missing))}. "
                f"Required: {', '.join(sorted(cls.REQUIRED_COLUMNS))}. "
                f"Note: Column names can have spaces (e.g., 'Book Value') or underscores (e.g., 'book_value')"
            )

        # Check that at least one value column exists (book_value OR market_value)
        has_value_column = bool(cls.VALUE_COLUMNS & headers_set)
        if not has_value_column:
            logger.error(f"Missing value column. Need 'book_value' or 'market_value'. Got: {headers_set}")
            raise ValidationError(
                f"Missing value column. CSV must contain either 'book_value' or 'market_value'. "
                f"Got columns: {', '.join(sorted(headers_set))}"
            )

        unknown = headers_set - cls.VALID_COLUMNS
        if unknown:
            logger.warning(f"Unknown columns will be ignored: {', '.join(sorted(unknown))}")

    @classmethod
    def validate_position(cls, position_dict: dict, row_number: int = 0) -> None:
        """Validate a single position.

        Args:
            position_dict: Position data as dict
            row_number: Row number (for error reporting)

        Raises:
            ValidationError: If position data invalid
        """
        # Check required fields
        for required_field in cls.REQUIRED_COLUMNS:
            if required_field not in position_dict or not position_dict[required_field]:
                raise ValidationError(
                    f"Row {row_number}: Missing required field '{required_field}'"
                )

        # Validate ticker format
        ticker = position_dict.get("ticker", "").strip()
        if not ticker:
            raise ValidationError(f"Row {row_number}: Ticker is empty")

        if "-" not in ticker:
            logger.warning(
                f"Row {row_number}: Ticker '{ticker}' may be in invalid format. "
                f"Expected format: TICKER-EXCHANGE (e.g., AAPL-US)"
            )

        # Validate quantity
        try:
            quantity = float(position_dict.get("quantity", ""))
            if quantity <= 0:
                raise ValidationError(f"Row {row_number}: Quantity must be positive, got {quantity}")
        except (ValueError, TypeError):
            raise ValidationError(
                f"Row {row_number}: Quantity '{position_dict.get('quantity')}' is not a valid number"
            )

        # Validate that at least one value column exists (book_value OR market_value)
        book_value = position_dict.get("book_value")
        market_value = position_dict.get("market_value")

        if not book_value and not market_value:
            raise ValidationError(
                f"Row {row_number}: Must have either 'book_value' or 'market_value'"
            )

        # Validate book value if present
        if book_value:
            try:
                book_value_val = float(book_value)
                if book_value_val < 0:
                    raise ValidationError(
                        f"Row {row_number}: Book value cannot be negative, got {book_value_val}"
                    )
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Row {row_number}: Book value '{book_value}' is not a valid number"
                )

        # Validate market value if present
        if market_value:
            try:
                market_value_val = float(market_value)
                if market_value_val < 0:
                    raise ValidationError(
                        f"Row {row_number}: Market value cannot be negative, got {market_value_val}"
                    )
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Row {row_number}: Market value '{market_value}' is not a valid number"
                )

        # Optional: validate cost basis if present
        cost_basis = position_dict.get("cost_basis")
        if cost_basis:
            try:
                cost_basis_val = float(cost_basis)
                if cost_basis_val < 0:
                    raise ValidationError(
                        f"Row {row_number}: Cost basis cannot be negative, got {cost_basis_val}"
                    )
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Row {row_number}: Cost basis '{cost_basis}' is not a valid number"
                )

    @classmethod
    def validate_no_duplicates(cls, positions: List) -> None:
        """Check for duplicate tickers in portfolio.

        Args:
            positions: List of position dicts or Position objects

        Raises:
            ValidationError: If duplicate tickers found
        """
        tickers = []
        for p in positions:
            # Handle both dict and Position objects
            if isinstance(p, dict):
                ticker = p.get("ticker", "").strip()
            else:
                # Assume it's a Position object
                ticker = p.ticker if hasattr(p, "ticker") else ""
            tickers.append(ticker)

        duplicates = [t for t in tickers if tickers.count(t) > 1]

        if duplicates:
            unique_duplicates = list(set(duplicates))
            raise ValidationError(
                f"Duplicate tickers found: {', '.join(sorted(unique_duplicates))}. "
                f"Each ticker must appear only once."
            )
