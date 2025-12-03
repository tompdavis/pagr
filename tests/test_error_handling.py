"""Tests for error handling throughout the pipeline."""

import pytest
from pagr.errors import (
    PagrError,
    CSVValidationError,
    PortfolioLoadError,
    FactSetAPIError,
    BondEnrichmentError,
    CompanyEnrichmentError,
    GraphBuildError,
    GraphQueryError,
    GraphSchemaError,
    ETLPipelineError,
    UIRenderError,
    ErrorCollector,
)


class TestPagrErrorBase:
    """Test base PagrError class."""

    def test_pagr_error_initialization(self):
        """Test creating PagrError with basic message."""
        error = PagrError("Test error message")
        assert str(error) == "Test error message"
        assert error.error_code == "UNKNOWN_ERROR"
        assert error.details == {}

    def test_pagr_error_with_code_and_details(self):
        """Test creating PagrError with error code and details."""
        details = {"row": 5, "column": "ticker"}
        error = PagrError("Test error", error_code="TEST_ERROR", details=details)
        assert error.error_code == "TEST_ERROR"
        assert error.details == details

    def test_pagr_error_string_representation(self):
        """Test string representation of error."""
        error = PagrError("Custom error message")
        assert "Custom error message" in str(error)


class TestCSVValidationError:
    """Test CSV validation errors."""

    def test_csv_validation_error_with_row_and_column(self):
        """Test CSV validation error with row and column info."""
        error = CSVValidationError("Invalid ticker format", row_number=5, column="ticker")
        assert error.row_number == 5
        assert error.column == "ticker"
        assert "Row 5" in str(error)
        assert "ticker" in str(error)

    def test_csv_validation_error_with_row_only(self):
        """Test CSV validation error with row number only."""
        error = CSVValidationError("Missing required field", row_number=3)
        assert "Row 3" in str(error)

    def test_csv_validation_error_code(self):
        """Test that CSV validation errors have correct code."""
        error = CSVValidationError("Some error")
        assert error.error_code == "CSV_VALIDATION_ERROR"


class TestFactSetAPIError:
    """Test FactSet API errors."""

    def test_factset_api_error_with_endpoint(self):
        """Test FactSet API error with endpoint information."""
        error = FactSetAPIError("Connection timeout", endpoint="/v1/companies", status_code=500)
        assert error.endpoint == "/v1/companies"
        assert error.status_code == 500
        assert error.error_code == "FACTSET_API_ERROR"

    def test_factset_api_error_with_retries(self):
        """Test FactSet API error with retry information."""
        error = FactSetAPIError("Max retries exceeded", retry_count=3)
        assert error.retry_count == 3
        assert "retried 3 times" in str(error)

    def test_factset_api_error_code(self):
        """Test that FactSet errors have correct code."""
        error = FactSetAPIError("API error")
        assert error.error_code == "FACTSET_API_ERROR"


class TestBondEnrichmentError:
    """Test bond enrichment errors."""

    def test_bond_enrichment_error_with_cusip(self):
        """Test bond enrichment error with CUSIP."""
        error = BondEnrichmentError("Bond not found", identifier="037833AA5", id_type="CUSIP")
        assert error.identifier == "037833AA5"
        assert error.id_type == "CUSIP"
        assert "037833AA5" in str(error)
        assert "CUSIP" in str(error)

    def test_bond_enrichment_error_with_isin(self):
        """Test bond enrichment error with ISIN."""
        error = BondEnrichmentError("Invalid ISIN", identifier="US912828Z772", id_type="ISIN")
        assert error.identifier == "US912828Z772"
        assert "US912828Z772" in str(error)

    def test_bond_enrichment_error_code(self):
        """Test that bond enrichment errors have correct code."""
        error = BondEnrichmentError("Error")
        assert error.error_code == "BOND_ENRICHMENT_ERROR"


class TestGraphQueryError:
    """Test graph query errors."""

    def test_graph_query_error_with_portfolio(self):
        """Test graph query error with portfolio name."""
        error = GraphQueryError("Query timeout", query_name="sector_exposure", portfolio_name="Portfolio A")
        assert error.query_name == "sector_exposure"
        assert error.portfolio_name == "Portfolio A"
        assert "sector_exposure" in str(error)
        assert "Portfolio A" in str(error)

    def test_graph_query_error_code(self):
        """Test that graph query errors have correct code."""
        error = GraphQueryError("Connection failed")
        assert error.error_code == "GRAPH_QUERY_ERROR"


class TestGraphSchemaError:
    """Test graph schema errors."""

    def test_graph_schema_error_with_versions(self):
        """Test graph schema error with version mismatch."""
        error = GraphSchemaError(
            "Schema mismatch",
            expected_schema="v2.0_with_bonds",
            detected_schema="v1.0_stocks_only"
        )
        assert error.details["expected_schema"] == "v2.0_with_bonds"
        assert error.details["detected_schema"] == "v1.0_stocks_only"
        assert "Re-upload" in str(error)

    def test_graph_schema_error_code(self):
        """Test that schema errors have correct code."""
        error = GraphSchemaError("Schema error")
        assert error.error_code == "GRAPH_SCHEMA_ERROR"


class TestErrorCollector:
    """Test ErrorCollector for collecting multiple errors."""

    def test_error_collector_add_single_error(self):
        """Test adding a single error."""
        collector = ErrorCollector()
        error = BondEnrichmentError("Test error")
        collector.add_error(error)

        assert collector.has_errors()
        assert len(collector.errors) == 1

    def test_error_collector_add_multiple_errors(self):
        """Test adding multiple errors."""
        collector = ErrorCollector()
        for i in range(5):
            error = CSVValidationError(f"Error {i}", row_number=i)
            collector.add_error(error)

        assert collector.has_errors()
        assert len(collector.errors) == 5

    def test_error_collector_add_warnings(self):
        """Test adding warnings."""
        collector = ErrorCollector()
        collector.add_warning("Warning 1")
        collector.add_warning("Warning 2")

        assert collector.has_warnings()
        assert len(collector.warnings) == 2

    def test_error_collector_max_errors(self):
        """Test that error collector respects max_errors limit."""
        collector = ErrorCollector(max_errors=3)
        for i in range(5):
            error = CSVValidationError(f"Error {i}", row_number=i)
            collector.add_error(error)

        # Should only collect first 3 errors
        assert len(collector.errors) == 3

    def test_error_collector_get_error_summary(self):
        """Test getting error summary."""
        collector = ErrorCollector()
        collector.add_error(BondEnrichmentError("Bond not found"))
        collector.add_error(FactSetAPIError("API timeout"))

        summary = collector.get_error_summary()
        assert "Errors (2)" in summary
        assert "BOND_ENRICHMENT_ERROR" in summary
        assert "FACTSET_API_ERROR" in summary

    def test_error_collector_get_warning_summary(self):
        """Test getting warning summary."""
        collector = ErrorCollector()
        collector.add_warning("Warning about bonds")
        collector.add_warning("Warning about API")

        summary = collector.get_warning_summary()
        assert "Warnings (2)" in summary
        assert "bonds" in summary
        assert "API" in summary

    def test_error_collector_clear(self):
        """Test clearing error collector."""
        collector = ErrorCollector()
        collector.add_error(BondEnrichmentError("Error"))
        collector.add_warning("Warning")

        assert collector.has_errors()
        assert collector.has_warnings()

        collector.clear()

        assert not collector.has_errors()
        assert not collector.has_warnings()

    def test_error_collector_summary_when_empty(self):
        """Test summary when no errors or warnings."""
        collector = ErrorCollector()
        assert collector.get_error_summary() == "No errors"
        assert collector.get_warning_summary() == "No warnings"


class TestPortfolioLoadError:
    """Test portfolio load errors."""

    def test_portfolio_load_error_with_file_path(self):
        """Test portfolio load error with file path."""
        error = PortfolioLoadError("File not found", file_path="/path/to/file.csv")
        assert error.file_path == "/path/to/file.csv"
        assert "/path/to/file.csv" in str(error)

    def test_portfolio_load_error_code(self):
        """Test portfolio load error code."""
        error = PortfolioLoadError("Error")
        assert error.error_code == "PORTFOLIO_LOAD_ERROR"


class TestUIRenderError:
    """Test UI render errors."""

    def test_ui_render_error_with_component(self):
        """Test UI render error with component name."""
        error = UIRenderError("Failed to render table", component="Positions Table")
        assert error.component == "Positions Table"
        assert "Positions Table" in str(error)

    def test_ui_render_error_code(self):
        """Test UI render error code."""
        error = UIRenderError("Error")
        assert error.error_code == "UI_RENDER_ERROR"


class TestETLPipelineError:
    """Test ETL pipeline errors."""

    def test_etl_pipeline_error_with_stage(self):
        """Test ETL pipeline error with stage information."""
        error = ETLPipelineError("Connection failed", stage="graph_build", position_count=150)
        assert error.stage == "graph_build"
        assert error.position_count == 150
        assert "graph_build" in str(error)

    def test_etl_pipeline_error_code(self):
        """Test ETL pipeline error code."""
        error = ETLPipelineError("Error")
        assert error.error_code == "ETL_PIPELINE_ERROR"
