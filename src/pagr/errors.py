"""Comprehensive error handling and custom exceptions for PAGR."""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class PagrError(Exception):
    """Base exception for all PAGR errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        """Initialize PAGR error.

        Args:
            message: User-friendly error message
            error_code: Unique error code for categorization
            details: Additional error details for logging
        """
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        """Return user-friendly error message."""
        return self.message

    def log_error(self):
        """Log error with full details."""
        logger.error(f"[{self.error_code}] {self.message}", extra=self.details)


# CSV/Portfolio Loading Errors


class CSVValidationError(PagrError):
    """Raised when CSV validation fails."""

    def __init__(self, message: str, row_number: Optional[int] = None, column: Optional[str] = None):
        """Initialize CSV validation error.

        Args:
            message: Error message
            row_number: Row number where error occurred
            column: Column name where error occurred
        """
        self.row_number = row_number
        self.column = column
        details = {}
        if row_number:
            details["row_number"] = row_number
        if column:
            details["column"] = column

        error_code = "CSV_VALIDATION_ERROR"
        if row_number and column:
            message = f"Row {row_number}, Column '{column}': {message}"
        elif row_number:
            message = f"Row {row_number}: {message}"

        super().__init__(message, error_code, details)


class PortfolioLoadError(PagrError):
    """Raised when portfolio loading fails."""

    def __init__(self, message: str, file_path: Optional[str] = None):
        """Initialize portfolio load error.

        Args:
            message: Error message
            file_path: Path to portfolio file
        """
        self.file_path = file_path
        details = {}
        if file_path:
            details["file_path"] = file_path
            message = f"Failed to load portfolio from {file_path}: {message}"

        super().__init__(message, "PORTFOLIO_LOAD_ERROR", details)


# FactSet API Errors


class FactSetAPIError(PagrError):
    """Raised when FactSet API call fails."""

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_count: int = 0,
    ):
        """Initialize FactSet API error.

        Args:
            message: Error message
            endpoint: API endpoint that failed
            status_code: HTTP status code
            retry_count: Number of retries attempted
        """
        self.endpoint = endpoint
        self.status_code = status_code
        self.retry_count = retry_count

        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        if status_code:
            details["status_code"] = status_code
        details["retry_count"] = retry_count

        if retry_count > 0:
            message = f"{message} (retried {retry_count} times)"

        super().__init__(message, "FACTSET_API_ERROR", details)


class BondEnrichmentError(PagrError):
    """Raised when bond enrichment fails."""

    def __init__(self, message: str, identifier: Optional[str] = None, id_type: Optional[str] = None):
        """Initialize bond enrichment error.

        Args:
            message: Error message
            identifier: Bond identifier (CUSIP/ISIN)
            id_type: Type of identifier
        """
        self.identifier = identifier
        self.id_type = id_type

        details = {}
        if identifier:
            details["identifier"] = identifier
        if id_type:
            details["id_type"] = id_type

        if identifier:
            message = f"Failed to enrich bond {id_type}:{identifier}: {message}"

        super().__init__(message, "BOND_ENRICHMENT_ERROR", details)


class CompanyEnrichmentError(PagrError):
    """Raised when company enrichment fails."""

    def __init__(self, message: str, company_name: Optional[str] = None, ticker: Optional[str] = None):
        """Initialize company enrichment error.

        Args:
            message: Error message
            company_name: Company name
            ticker: Company ticker
        """
        self.company_name = company_name
        self.ticker = ticker

        details = {}
        if company_name:
            details["company_name"] = company_name
        if ticker:
            details["ticker"] = ticker

        identifier = ticker or company_name or "Unknown"
        message = f"Failed to enrich company {identifier}: {message}"

        super().__init__(message, "COMPANY_ENRICHMENT_ERROR", details)


# Graph Errors


class GraphBuildError(PagrError):
    """Raised when graph building fails."""

    def __init__(message: str, node_type: Optional[str] = None, error_details: Optional[str] = None):
        """Initialize graph build error.

        Args:
            message: Error message
            node_type: Type of node being built
            error_details: Detailed error from graph database
        """
        details = {}
        if node_type:
            details["node_type"] = node_type
        if error_details:
            details["graph_error"] = error_details

        if node_type:
            message = f"Failed to build {node_type} nodes: {message}"

        super().__init__(message, "GRAPH_BUILD_ERROR", details)


class GraphQueryError(PagrError):
    """Raised when graph query fails."""

    def __init__(self, message: str, query_name: Optional[str] = None, portfolio_name: Optional[str] = None):
        """Initialize graph query error.

        Args:
            message: Error message
            query_name: Name of query that failed
            portfolio_name: Portfolio being queried
        """
        self.query_name = query_name
        self.portfolio_name = portfolio_name

        details = {}
        if query_name:
            details["query_name"] = query_name
        if portfolio_name:
            details["portfolio_name"] = portfolio_name

        context = []
        if portfolio_name:
            context.append(f"portfolio '{portfolio_name}'")
        if query_name:
            context.append(f"query '{query_name}'")

        if context:
            message = f"Query failed for {', '.join(context)}: {message}"

        super().__init__(message, "GRAPH_QUERY_ERROR", details)


class GraphSchemaError(PagrError):
    """Raised when graph schema mismatch is detected."""

    def __init__(self, message: str, expected_schema: Optional[str] = None, detected_schema: Optional[str] = None):
        """Initialize graph schema error.

        Args:
            message: Error message
            expected_schema: Expected schema version/structure
            detected_schema: Detected schema version/structure
        """
        details = {}
        if expected_schema:
            details["expected_schema"] = expected_schema
        if detected_schema:
            details["detected_schema"] = detected_schema

        if expected_schema and detected_schema:
            message += f"\nExpected: {expected_schema}\nDetected: {detected_schema}\nRe-upload your portfolio to migrate to the new schema."

        super().__init__(message, "GRAPH_SCHEMA_ERROR", details)


# Pipeline Errors


class ETLPipelineError(PagrError):
    """Raised when ETL pipeline fails."""

    def __init__(self, message: str, stage: Optional[str] = None, position_count: int = 0):
        """Initialize ETL pipeline error.

        Args:
            message: Error message
            stage: Pipeline stage that failed (load, validate, enrich, build_graph)
            position_count: Number of positions processed before error
        """
        self.stage = stage
        self.position_count = position_count

        details = {"stage": stage, "positions_processed": position_count}

        if stage:
            message = f"ETL pipeline failed at '{stage}' stage: {message}"

        super().__init__(message, "ETL_PIPELINE_ERROR", details)


# UI/Display Errors


class UIRenderError(PagrError):
    """Raised when UI rendering fails."""

    def __init__(self, message: str, component: Optional[str] = None):
        """Initialize UI render error.

        Args:
            message: Error message
            component: UI component that failed to render
        """
        self.component = component
        details = {}
        if component:
            details["component"] = component
            message = f"Failed to render {component}: {message}"

        super().__init__(message, "UI_RENDER_ERROR", details)


# Error Collection and Reporting


class ErrorCollector:
    """Collects and reports errors during processing."""

    def __init__(self, max_errors: int = 100):
        """Initialize error collector.

        Args:
            max_errors: Maximum number of errors to collect before stopping
        """
        self.max_errors = max_errors
        self.errors: List[PagrError] = []
        self.warnings: List[str] = []

    def add_error(self, error: PagrError):
        """Add an error to the collection.

        Args:
            error: Error to add
        """
        if len(self.errors) < self.max_errors:
            self.errors.append(error)
            error.log_error()
        else:
            logger.warning(f"Error limit ({self.max_errors}) reached. Additional errors will not be collected.")

    def add_warning(self, warning: str):
        """Add a warning to the collection.

        Args:
            warning: Warning message
        """
        self.warnings.append(warning)
        logger.warning(warning)

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0

    def get_error_summary(self) -> str:
        """Get a summary of all errors.

        Returns:
            String summary of errors
        """
        if not self.has_errors():
            return "No errors"

        lines = [f"Errors ({len(self.errors)}):"]
        for i, error in enumerate(self.errors, 1):
            lines.append(f"  {i}. [{error.error_code}] {error.message}")

        return "\n".join(lines)

    def get_warning_summary(self) -> str:
        """Get a summary of all warnings.

        Returns:
            String summary of warnings
        """
        if not self.has_warnings():
            return "No warnings"

        lines = [f"Warnings ({len(self.warnings)}):"]
        for i, warning in enumerate(self.warnings, 1):
            lines.append(f"  {i}. {warning}")

        return "\n".join(lines)

    def clear(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
