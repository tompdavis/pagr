# Error Handling Reference

## Overview

PAGR v2.0 includes comprehensive error handling with descriptive messages to help diagnose and fix issues quickly. This guide documents all error types and solutions.

## Error Categories

### 1. CSV Validation Errors

Errors that occur when loading and validating portfolio CSV files.

#### `CSV_VALIDATION_ERROR: Missing required field`

**Cause**: Required column missing or empty

**Common Cases**:
- Missing `quantity` column
- Missing `book_value` (or `market_value`) column
- Empty values in required fields

**Example Message**:
```
Row 3, Column 'quantity': Missing required field 'quantity'
```

**Solution**:
```csv
# ❌ Missing quantity
AAPL-US,,10000.00,Common Stock

# ✅ Add quantity
AAPL-US,100,10000.00,Common Stock
```

#### `CSV_VALIDATION_ERROR: Must provide at least one identifier`

**Cause**: Position has no ticker, ISIN, or CUSIP

**Example Message**:
```
Row 5: Must provide at least one identifier: ticker, isin, or cusip
```

**Solution**:
```csv
# ❌ No identifier
,100,10000.00,Corporate Bond

# ✅ Add CUSIP
,100,10000.00,Corporate Bond,,037833AA5

# ✅ Or add ISIN
,100,10000.00,Treasury Bond,US912828Z772,

# ✅ Or for stocks, add ticker
AAPL-US,100,10000.00,Common Stock
```

#### `CSV_VALIDATION_ERROR: Quantity must be positive`

**Cause**: Quantity is zero, negative, or not a number

**Example Message**:
```
Row 2: Quantity must be positive, got -50
```

**Solution**:
```csv
# ❌ Invalid quantities
AAPL-US,0,10000.00,Common Stock
AAPL-US,-50,10000.00,Common Stock
AAPL-US,abc,10000.00,Common Stock

# ✅ Valid quantity
AAPL-US,100,10000.00,Common Stock
AAPL-US,100.5,10000.00,Common Stock
```

#### `CSV_VALIDATION_ERROR: Book value cannot be negative`

**Cause**: Book value is negative

**Example Message**:
```
Row 4: Book value cannot be negative, got -500
```

**Solution**:
```csv
# ❌ Negative book value
MSFT-US,50,-500.00,Common Stock

# ✅ Positive or zero
MSFT-US,50,21000.00,Common Stock
MSFT-US,50,0.00,Common Stock
```

#### `CSV_VALIDATION_ERROR: Value is not a valid number`

**Cause**: Numeric field contains non-numeric text

**Example Message**:
```
Row 6: Quantity 'abc' is not a valid number
```

**Solution**:
```csv
# ❌ Invalid numeric values
AAPL-US,hundred,10000.00,Common Stock
AAPL-US,100,ten thousand,Common Stock

# ✅ Valid numeric values
AAPL-US,100,10000.00,Common Stock
AAPL-US,100.50,10000.50,Common Stock
```

#### `CSV_VALIDATION_ERROR: Ticker may be in invalid format`

**Severity**: Warning (file still uploads)

**Cause**: Stock ticker missing exchange code

**Example Message**:
```
Row 1: Ticker 'AAPL' may be in invalid format.
Expected format: TICKER-EXCHANGE (e.g., AAPL-US)
```

**Solution**:
```csv
# ⚠️  Works but shows warning
AAPL,100,10000.00,Common Stock

# ✅ Recommended format
AAPL-US,100,10000.00,Common Stock
```

### 2. Portfolio Loading Errors

Errors that occur when loading portfolio files.

#### `PORTFOLIO_LOAD_ERROR: File not found`

**Cause**: CSV file path doesn't exist

**Example Message**:
```
Failed to load portfolio from /path/to/file.csv: File not found
```

**Solution**:
```python
# ❌ File doesn't exist
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
portfolio = PortfolioLoader.load("nonexistent.csv")

# ✅ Verify file exists
import os
if os.path.exists("my_portfolio.csv"):
    portfolio = PortfolioLoader.load("my_portfolio.csv")
```

#### `PORTFOLIO_LOAD_ERROR: Invalid CSV format`

**Cause**: File is not valid CSV or encoding is wrong

**Example Message**:
```
Failed to load portfolio from file.csv: Invalid CSV format
```

**Solution**:
1. Ensure file is saved as CSV (not XLS, XLSX, etc.)
2. Check file encoding (should be UTF-8)
3. Verify file doesn't have extra characters or BOM

### 3. FactSet API Errors

Errors that occur when communicating with FactSet API.

#### `FACTSET_API_ERROR: Authentication failed`

**Cause**: Invalid FactSet credentials

**Example Message**:
```
[FACTSET_API_ERROR] Invalid credentials. Check FDS_USERNAME and FDS_API_KEY.
```

**Solution**:
```bash
# 1. Check environment variables
echo $FDS_USERNAME
echo $FDS_API_KEY

# 2. Set correct credentials
export FDS_USERNAME="your-username-serial"
export FDS_API_KEY="your-api-key"

# 3. Verify format (should be: USERNAME-SERIAL)
# Example: john-doe-001
```

#### `FACTSET_API_ERROR: Rate limit exceeded`

**Cause**: Too many API requests in short time

**Example Message**:
```
[FACTSET_API_ERROR] Rate limited. Waiting 5 seconds before retry...
```

**Solution**:
- Wait for retry to complete (automatic)
- Reduce number of positions if uploading very large portfolio
- Split portfolio into smaller batches

#### `FACTSET_API_ERROR: Request timeout`

**Cause**: FactSet API taking too long to respond

**Example Message**:
```
[FACTSET_API_ERROR] Request timeout after 30 seconds
```

**Solution**:
- Retry upload (will automatically retry up to 3 times)
- Check internet connection
- Try again later if FactSet services are slow

#### `FACTSET_API_ERROR: Endpoint not found (404)`

**Cause**: API endpoint doesn't exist

**Example Message**:
```
[FACTSET_API_ERROR] Endpoint not found: /content/factset-api/v1/endpoint
```

**Solution**: Upgrade PAGR to latest version. This usually indicates version mismatch.

### 4. Bond Enrichment Errors

Errors specific to bond data enrichment.

#### `BOND_ENRICHMENT_ERROR: Must provide identifier`

**Cause**: Bond position has no CUSIP or ISIN

**Example Message**:
```
[BOND_ENRICHMENT_ERROR] Must provide either CUSIP or ISIN identifier
```

**Solution**:
```csv
# ❌ Missing bond identifier
,500,50000.00,Corporate Bond

# ✅ With CUSIP
,500,50000.00,Corporate Bond,,037833AA5

# ✅ With ISIN
,500,50000.00,Corporate Bond,US912828Z772,
```

#### `BOND_ENRICHMENT_ERROR: Bond not found in FactSet`

**Cause**: Bond identifier not in FactSet database

**Example Message**:
```
[BOND_ENRICHMENT_ERROR] Failed to enrich bond CUSIP:123456ABC:
Bond not found in FactSet
```

**Solution**:
- Verify CUSIP/ISIN is correct
- Try alternative identifier (ISIN if CUSIP not found)
- Position will still load with basic data (price and coupon marked as N/A)

#### `BOND_ENRICHMENT_ERROR: Unexpected error during enrichment`

**Cause**: Unexpected error during enrichment

**Example Message**:
```
[BOND_ENRICHMENT_ERROR] Failed to enrich bond CUSIP:037833AA5:
Unexpected error: Connection reset
```

**Solution**:
- Retry upload (enrichment uses automatic retry)
- Check internet connection
- Contact support if persists

### 5. Graph Query Errors

Errors that occur when querying the graph database.

#### `GRAPH_QUERY_ERROR: Query timeout`

**Cause**: Graph query taking too long

**Example Message**:
```
[GRAPH_QUERY_ERROR] Query failed for portfolio 'My Portfolio',
query 'sector_exposure': Query timed out after 30 seconds
```

**Solution**:
- Portfolio may be too large
- Try simplifying view (drill-down to specific sectors)
- Restart application

#### `GRAPH_QUERY_ERROR: Connection failed`

**Cause**: Cannot connect to graph database

**Example Message**:
```
[GRAPH_QUERY_ERROR] Query failed for portfolio 'My Portfolio':
Connection refused: memgraph server not running
```

**Solution**:
```bash
# 1. Verify Memgraph is running
docker ps | grep memgraph

# 2. Start Memgraph if not running
docker-compose up memgraph

# 3. Check connection configuration
# Verify MEMGRAPH_URI env variable
```

### 6. Graph Schema Errors

Errors related to graph database schema mismatches.

#### `GRAPH_SCHEMA_ERROR: Schema mismatch detected`

**Cause**: Portfolio created with different schema version

**Example Message**:
```
[GRAPH_SCHEMA_ERROR] Schema mismatch detected
Expected: v2.0_with_bonds
Detected: v1.0_stocks_only
Re-upload your portfolio to migrate to the new schema.
```

**Solution**:
1. This is expected when upgrading from v1.0 to v2.0
2. Re-upload portfolio with updated CSV format:
```python
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
portfolio = PortfolioLoader.load("updated_portfolio.csv")
# Portfolio will be created with new v2.0 schema
```

### 7. UI Render Errors

Errors that occur when rendering UI components.

#### `UI_RENDER_ERROR: Failed to render table`

**Cause**: Error formatting data for display

**Example Message**:
```
❌ Error displaying positions: Failed to render table
```

**Solution**:
- Reload page/application
- Try with smaller portfolio first
- Check browser console for details

#### `UI_RENDER_ERROR: Failed to render chart`

**Cause**: Error creating visualization

**Example Message**:
```
❌ Error displaying sector exposure: Failed to render chart
```

**Solution**:
- Some positions may have invalid data
- Try drilling down to specific sectors
- Reload application if persists

## Error Levels

### Errors (Block Processing)
- ❌ Red color
- Stop processing
- Require user action
- Examples: Missing required field, authentication failed

### Warnings (Non-Blocking)
- ⚠️  Yellow/Orange color
- Processing continues
- Alert user to potential issues
- Examples: Invalid ticker format, missing enrichment data

### Info (Informational)
- ℹ️  Blue color
- Processing continues normally
- Helpful information
- Examples: Position loaded successfully

## Common Error Combinations

### Scenario 1: CSV Upload Fails for Multiple Reasons

```
Row 1: Missing required field 'quantity'
Row 3: Quantity 'fifty' is not a valid number
Row 5: Must provide at least one identifier: ticker, isin, or cusip
```

**Solution**: Fix all rows mentioned before re-uploading.

### Scenario 2: Upload Succeeds but Bonds Not Enriched

```
⚠️  Warning: Bond not found in FactSet for CUSIP:INVALID001
⚠️  Warning: Could not fetch FactSet data for CUSIP:INVALID001

Portfolio loaded successfully with 5 positions
- 3 stocks enriched
- 2 bonds loaded with incomplete data (N/A for price and coupon)
```

**Solution**: Verify bond identifiers are correct. Bonds will still work but prices/coupons unavailable.

### Scenario 3: Graph Database Issues

```
❌ Error querying sector exposure: Connection refused
❌ Error querying country breakdown: Connection refused
```

**Solution**:
1. Check Memgraph is running
2. Restart graph database service
3. Reload application

## Debugging Tips

### 1. Enable Detailed Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all operations will show detailed logs
```

### 2. Check Environment Variables

```bash
# Verify FactSet credentials are set
env | grep FDS_

# Verify Memgraph connection
env | grep MEMGRAPH_
```

### 3. Validate CSV Manually

```python
from pagr.fds.loaders.validator import PositionValidator

# Test specific row
position_dict = {
    "ticker": "AAPL-US",
    "quantity": "100",
    "book_value": "19000.00"
}

try:
    PositionValidator.validate_position(position_dict, row_number=1)
    print("✓ Valid")
except Exception as e:
    print(f"✗ Error: {e}")
```

### 4. Test FactSet Connectivity

```python
from pagr.fds.clients.factset_client import FactSetClient

client = FactSetClient(username="USER", api_key="KEY")

try:
    result = client.get_company_profile(["AAPL-US"])
    print("✓ FactSet API working")
except Exception as e:
    print(f"✗ FactSet error: {e}")
```

## Getting Help

If you encounter an error not covered here:

1. **Note the error code** (e.g., `CSV_VALIDATION_ERROR`)
2. **Note the full error message** including details
3. **Collect relevant context**:
   - Sample CSV rows that caused the error
   - Environment variables being used
   - Operation being performed
4. **Check logs** for additional information
5. **See related documentation**:
   - [CSV_FORMAT.md](CSV_FORMAT.md) for format issues
   - [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
   - [ARCHITECTURE.md](ARCHITECTURE.md) for system overview

## Summary

| Error Code | Severity | Solution |
|-----------|----------|----------|
| CSV_VALIDATION_ERROR | Error | Fix CSV format per error message |
| PORTFOLIO_LOAD_ERROR | Error | Verify file exists and is readable |
| FACTSET_API_ERROR | Error | Check credentials, retry upload |
| BOND_ENRICHMENT_ERROR | Warning | Verify bond identifiers, may load with N/A |
| GRAPH_QUERY_ERROR | Error | Restart database, reduce portfolio size |
| GRAPH_SCHEMA_ERROR | Error | Re-upload portfolio with new schema |
| UI_RENDER_ERROR | Warning | Reload page, try simpler view |

Most errors can be resolved by:
1. Reading the error message carefully
2. Checking the solution in this guide
3. Retrying the operation
4. Contacting support if persists
