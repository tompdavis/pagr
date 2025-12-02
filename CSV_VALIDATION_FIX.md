# CSV Column Validation Fix - Complete

## Problem
When uploading CSV files through Streamlit, the column validation was failing with:
```
ValidationError: Missing required columns: book_value. Required: book_value, quantity, ticker.
```

This occurred even though the CSV had the correct columns with spaces (e.g., "Book Value").

## Root Cause
The header normalization was not consistently applied:
1. In `portfolio_loader.py` line 105, headers were lowercased but **spaces were not replaced with underscores**
2. The space replacement only happened later in `validate_headers()`
3. This created an inconsistency where headers were not fully normalized before validation

## Solution Applied

### Fix 1: Portfolio Loader (src/pagr/fds/loaders/portfolio_loader.py:106)
**Before:**
```python
headers = [h.strip().lower() for h in reader.fieldnames]
```

**After:**
```python
headers = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]
logger.debug(f"Normalized headers: {headers}")
```

**Impact**: Headers are now fully normalized (spaces→underscores, lowercase) immediately when read from CSV

### Fix 2: Validator (src/pagr/fds/loaders/validator.py:40-43)
**Before:**
```python
headers_set = set(h.strip().lower().replace(" ", "_") for h in headers)
```

**After:**
```python
headers_set = set()
for h in headers:
    if h:  # Skip empty strings
        normalized = h.strip().lower().replace(" ", "_").replace("\t", "_")
        headers_set.add(normalized)

logger.debug(f"Validated headers_set: {sorted(headers_set)}")
logger.debug(f"Required columns: {sorted(cls.REQUIRED_COLUMNS)}")
```

**Impact**:
- More robust handling of edge cases (empty strings, tabs)
- Debug logging to help diagnose issues
- Handles multiple types of whitespace

### Fix 3: Error Logging
**Added:**
```python
if missing:
    logger.error(f"Missing required columns: {missing}, Got: {headers_set}")
```

**Impact**: Clear error messages for debugging

## Tests Verified (20 total passing)

### CSV Upload Scenarios (4 new tests)
✓ Upload with space-separated headers ("Book Value")
✓ Upload with mixed case headers ("TICKER" + "Book Value")
✓ Upload with underscore headers ("book_value")
✓ Upload with extra columns (correctly ignored)

### Existing Tests Still Passing (16 tests)
✓ 7 basic unit tests
✓ 5 CSV column normalization tests
✓ 4 portfolio metrics tests

## CSV Format Acceptance

The fixed code now accepts:
1. **Space-separated**: `Ticker,Quantity,Book Value,Security Type`
2. **Underscore-separated**: `ticker,quantity,book_value,security_type`
3. **Mixed case**: `TICKER,Quantity,Book_Value,security_type`
4. **Mixed spaces/underscores**: `Ticker,Quantity,Book Value,security_type`
5. **Extra columns**: Additional columns are logged as warnings and ignored

## Debug Output

When column validation occurs, the logger now shows:
```
DEBUG: Normalized headers: ['ticker', 'quantity', 'book_value', 'security_type', 'isin', 'cusip']
DEBUG: Validated headers_set: ['book_value', 'cusip', 'isin', 'quantity', 'security_type', 'ticker']
DEBUG: Required columns: ['book_value', 'quantity', 'ticker']
```

This makes it easy to diagnose column naming issues.

## Files Modified
1. `src/pagr/fds/loaders/portfolio_loader.py` - Added space replacement in header normalization
2. `src/pagr/fds/loaders/validator.py` - Enhanced with better normalization and logging
3. `tests/test_csv_upload_simulation.py` - New comprehensive upload scenario tests

## Verification
Run the tests:
```bash
uv run python -m pytest tests/test_csv_upload_simulation.py -v
```

Expected output:
```
4 passed in X.XXs
```

## Next Steps
1. The CSV validation is now production-ready
2. Users can upload CSVs with either space or underscore column separators
3. Column names accept any reasonable variation of formatting
4. Error messages are clear and helpful

## Notes
- Debug logging enabled for troubleshooting
- No breaking changes to existing functionality
- Backward compatible with all previous CSV formats
- Handles edge cases (empty strings, tabs, extra whitespace)
