"""Portfolio loader for CSV files."""

import csv
import logging
from pathlib import Path
from typing import Optional

from pagr.fds.models.portfolio import Portfolio, Position
from pagr.fds.loaders.validator import PositionValidator, ValidationError

logger = logging.getLogger(__name__)


class PortfolioLoaderError(Exception):
    """Base exception for portfolio loader errors."""

    pass


class PortfolioLoader:
    """Loads portfolio data from CSV files."""

    SUPPORTED_FORMATS = {"csv"}

    def __init__(self):
        """Initialize portfolio loader."""
        pass

    @classmethod
    def load(cls, file_path: str, portfolio_name: Optional[str] = None) -> Portfolio:
        """Load portfolio from CSV file.

        CSV format (supports both stocks and bonds):
            ticker,quantity,book_value,security_type,isin,cusip
            AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
            MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
            ,500,50000.00,Corporate Bond,US037833AA56,037833AA5
            ,300,30000.00,Treasury Bond,US912828Z772,

        Args:
            file_path: Path to CSV file
            portfolio_name: Optional name for portfolio

        Returns:
            Portfolio object with loaded positions

        Raises:
            FileNotFoundError: If file doesn't exist
            PortfolioLoaderError: If file format invalid or data invalid
            ValidationError: If position data invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Portfolio file not found: {file_path}")

        if path.suffix.lower() != ".csv":
            raise PortfolioLoaderError(f"Unsupported file format: {path.suffix}. Expected: .csv")

        logger.info(f"Loading portfolio from {file_path}")

        try:
            positions = cls._read_csv(path)
        except ValidationError as e:
            raise PortfolioLoaderError(f"Validation error: {e}") from e
        except Exception as e:
            raise PortfolioLoaderError(f"Error reading CSV file: {e}") from e

        # Create portfolio
        portfolio = Portfolio(
            name=portfolio_name or path.stem,
            positions=positions,
        )

        # Calculate weights
        portfolio.calculate_weights()

        logger.info(
            f"Successfully loaded portfolio with {len(positions)} positions. "
            f"Total value: ${portfolio.total_value:,.2f}"
        )

        return portfolio

    @staticmethod
    def _read_csv(file_path: Path) -> list[Position]:
        """Read and parse CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of Position objects

        Raises:
            ValidationError: If data invalid
        """
        positions = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise PortfolioLoaderError("CSV file is empty")

            # Normalize and validate headers
            # Replace spaces with underscores and convert to lowercase
            headers = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]
            logger.debug(f"Normalized headers: {headers}")
            PositionValidator.validate_headers(headers)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                try:
                    # Normalize keys to lowercase and replace spaces with underscores
                    normalized_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}

                    # Validate position
                    PositionValidator.validate_position(normalized_row, row_num)

                    # Create Position object
                    # Support both book_value and market_value columns
                    # Prefer book_value, fall back to market_value if present
                    if "book_value" in normalized_row and normalized_row["book_value"]:
                        book_value = float(normalized_row["book_value"])
                    elif "market_value" in normalized_row and normalized_row["market_value"]:
                        book_value = float(normalized_row["market_value"])
                        logger.info(f"Row {row_num}: Using market_value as book_value")
                    else:
                        raise ValueError(f"Row {row_num}: Must have either 'book_value' or 'market_value'")

                    # Handle ticker (may be empty/None for bonds)
                    ticker_str = normalized_row.get("ticker", "").strip()
                    # Treat N/A, null, and empty string as None
                    ticker = None
                    if ticker_str and ticker_str.lower() not in ["n/a", "null"]:
                        ticker = ticker_str.upper()

                    # Get identifiers
                    isin = normalized_row.get("isin", "").strip() or None
                    cusip = normalized_row.get("cusip", "").strip() or None

                    # Clean up N/A values
                    if isin and isin.lower() == "n/a":
                        isin = None
                    if cusip and cusip.lower() == "n/a":
                        cusip = None

                    position = Position(
                        ticker=ticker,
                        quantity=float(normalized_row["quantity"]),
                        book_value=book_value,
                        security_type=normalized_row.get("security_type", "Common Stock").strip(),
                        isin=isin,
                        cusip=cusip,
                        market_value=(
                            float(normalized_row["market_value"])
                            if normalized_row.get("market_value") and "market_value" != "book_value"
                            else None
                        ),
                        purchase_date=normalized_row.get("purchase_date", "").strip() or None,
                    )

                    positions.append(position)

                    # Log with primary identifier for clarity
                    id_type, id_value = position.get_primary_identifier()
                    logger.debug(
                        f"Row {row_num}: Loaded {id_type}:{id_value} - "
                        f"{position.quantity} units @ ${position.book_value:,.2f} book value"
                    )

                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(f"Row {row_num}: Error parsing row: {e}") from e

        # Check for duplicates
        PositionValidator.validate_no_duplicates(positions)

        if not positions:
            raise PortfolioLoaderError("No positions found in CSV file")

        logger.info(f"Parsed {len(positions)} positions from CSV")

        return positions

    @staticmethod
    def create_sample_csv(file_path: str = "data/sample_portfolio.csv") -> None:
        """Create a sample portfolio CSV file with stocks and bonds.

        Args:
            file_path: Path where to create sample file
        """
        sample_data = [
            ["ticker", "quantity", "book_value", "security_type", "isin", "cusip"],
            # Stocks
            ["AAPL-US", "100", "19000.00", "Common Stock", "US0378331005", "037833100"],
            ["MSFT-US", "50", "21000.00", "Common Stock", "US5949181045", "594918104"],
            ["TSMC-TT", "200", "32000.00", "Common Stock", "US8740391003", "874039100"],
            # Bonds (note: ticker is empty/null for bonds)
            ["", "500", "50000.00", "Corporate Bond", "US037833AA56", "037833AA5"],
            ["", "300", "30000.00", "Treasury Bond", "US912828Z772", "912828Z77"],
        ]

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(sample_data)

        logger.info(f"Created sample portfolio CSV at {file_path} (includes stocks and bonds)")
