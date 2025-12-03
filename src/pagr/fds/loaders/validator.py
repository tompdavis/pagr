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
    REQUIRED_COLUMNS = {"quantity"}
    # Identifier columns: At least ONE of ticker, isin, or cusip is required
    IDENTIFIER_COLUMNS = {"ticker", "isin", "cusip"}
    VALUE_COLUMNS = {"book_value", "market_value"}  # At least one required

    # Optional columns
    OPTIONAL_COLUMNS = {"security_type", "purchase_date"}

    # All valid columns
    VALID_COLUMNS = REQUIRED_COLUMNS | IDENTIFIER_COLUMNS | VALUE_COLUMNS | OPTIONAL_COLUMNS

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
        logger.debug(f"Identifier columns (need at least one): {sorted(cls.IDENTIFIER_COLUMNS)}")
        logger.debug(f"Value columns (book_value OR market_value): {sorted(cls.VALUE_COLUMNS)}")

        # Check required columns
        missing = cls.REQUIRED_COLUMNS - headers_set
        if missing:
            logger.error(f"Missing required columns: {missing}, Got: {headers_set}")
            raise ValidationError(
                f"Missing required columns: {', '.join(sorted(missing))}. "
                f"Required: {', '.join(sorted(cls.REQUIRED_COLUMNS))}. "
                f"Note: Column names can have spaces (e.g., 'Book Value') or underscores (e.g., 'book_value')"
            )

        # Check that at least one identifier column exists (ticker OR isin OR cusip)
        has_identifier = bool(cls.IDENTIFIER_COLUMNS & headers_set)
        if not has_identifier:
            logger.error(f"Missing identifier columns. Need at least one of: ticker, isin, cusip. Got: {headers_set}")
            raise ValidationError(
                f"Missing identifier columns. CSV must contain at least one of: ticker, isin, or cusip. "
                f"Got columns: {', '.join(sorted(headers_set))}"
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

        # Validate identifiers: at least one of ticker, isin, cusip must be provided
        ticker = position_dict.get("ticker", "").strip()
        isin = position_dict.get("isin", "").strip()
        cusip = position_dict.get("cusip", "").strip()

        # Treat N/A, null, and empty string as missing
        ticker = ticker if ticker and ticker.lower() != "n/a" and ticker.lower() != "null" else ""
        isin = isin if isin and isin.lower() != "n/a" and isin.lower() != "null" else ""
        cusip = cusip if cusip and cusip.lower() != "n/a" and cusip.lower() != "null" else ""

        if not any([ticker, isin, cusip]):
            raise ValidationError(
                f"Row {row_number}: Must provide at least one identifier: ticker, isin, or cusip"
            )

        # Validate ticker format if provided
        if ticker and "-" not in ticker:
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
        """Check for duplicate identifiers in portfolio.

        For stocks: ticker must be unique
        For bonds: (isin, cusip) pair must be unique

        Args:
            positions: List of Position objects

        Raises:
            ValidationError: If duplicate identifiers found
        """
        identifiers = []
        duplicate_info = []

        for p in positions:
            # Get primary identifier
            if hasattr(p, "get_primary_identifier"):
                id_type, id_value = p.get_primary_identifier()
                identifier_str = f"{id_type}:{id_value}"
                identifiers.append(identifier_str)
            elif isinstance(p, dict):
                # Fallback for dict
                ticker = p.get("ticker", "").strip() or None
                isin = p.get("isin", "").strip() or None
                cusip = p.get("cusip", "").strip() or None

                if cusip:
                    id_type, id_value = "cusip", cusip
                elif isin:
                    id_type, id_value = "isin", isin
                elif ticker:
                    id_type, id_value = "ticker", ticker
                else:
                    continue

                identifier_str = f"{id_type}:{id_value}"
                identifiers.append(identifier_str)

        # Find duplicates
        seen = set()
        duplicates = []
        for identifier in identifiers:
            if identifier in seen:
                duplicates.append(identifier)
            seen.add(identifier)

        if duplicates:
            unique_duplicates = list(set(duplicates))
            raise ValidationError(
                f"Duplicate identifiers found: {', '.join(sorted(unique_duplicates))}. "
                f"Each security identifier must appear only once in the portfolio."
            )
