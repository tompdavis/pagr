# Backward Compatibility Fix - CSV market_value Column Support

## Problem
User's CSV files contain `market_value` column instead of `book_value`, causing validation errors:
```
ValidationError: Missing required columns: book_value
Got: {'cusip', 'security_type', 'quantity', 'ticker', 'isin', 'market_value'}
```

## Root Cause
The code was changed to require `book_value` (cost basis), but many existing CSV files use `market_value` (current price). The validator only accepted `book_value` and rejected CSVs with `market_value`.

## Solution: Accept Either Column

### Changes Made

#### 1. Validator (src/pagr/fds/loaders/validator.py)

**Changed:** Required columns definition
```python
# BEFORE: Strict requirement for book_value
REQUIRED_COLUMNS = {"ticker", "quantity", "book_value"}

# AFTER: Allow either book_value OR market_value
REQUIRED_COLUMNS = {"ticker", "quantity"}
VALUE_COLUMNS = {"book_value", "market_value"}  # At least one required
```

**Changed:** Header validation
```python
# BEFORE: Only checked for book_value
missing = cls.REQUIRED_COLUMNS - headers_set

# AFTER: Checks for at least one value column
has_value_column = bool(cls.VALUE_COLUMNS & headers_set)
if not has_value_column:
    raise ValidationError("Must contain either 'book_value' or 'market_value'")
```

**Changed:** Position validation
```python
# BEFORE: Required book_value field
book_value = float(position_dict.get("book_value", ""))

# AFTER: Accept either book_value OR market_value
book_value = position_dict.get("book_value")
market_value = position_dict.get("market_value")

if not book_value and not market_value:
    raise ValidationError("Must have either 'book_value' or 'market_value'")
```

#### 2. Portfolio Loader (src/pagr/fds/loaders/portfolio_loader.py)

**Added:** Smart value column handling
```python
# If CSV has book_value, use it
if "book_value" in normalized_row and normalized_row["book_value"]:
    book_value = float(normalized_row["book_value"])

# Otherwise, fall back to market_value
elif "market_value" in normalized_row and normalized_row["market_value"]:
    book_value = float(normalized_row["market_value"])
    logger.info(f"Using market_value as book_value for {ticker}")

else:
    raise ValueError("Must have either 'book_value' or 'market_value'")
```

## CSV Formats Now Supported

| Format | Column Name | Status | Example |
|--------|------------|--------|---------|
| New (cost basis) | `book_value` | ✓ Preferred | `Ticker,Quantity,Book Value` |
| Old (current price) | `market_value` | ✓ Supported | `Ticker,Quantity,Market Value` |
| Both columns | Both present | ✓ Supported | `Ticker,Quantity,Book Value,Market Value` |
| With spaces | `Book Value` | ✓ Supported | Automatically normalized |
| With underscores | `book_value` | ✓ Supported | Already normalized |
| Mixed case | `Market_Value` | ✓ Supported | Case-insensitive |

## Test Results: 23/23 PASSING ✓

### New Tests Added:
```
test_market_value_column.py::test_market_value_column PASSED
test_market_value_column.py::test_book_value_column PASSED
test_market_value_column.py::test_both_columns PASSED
```

### All Existing Tests Still Pass:
```
7 basic tests
5 column normalization tests
4 upload simulation tests
4 portfolio metrics tests
```

## How It Works

### Priority System:
1. **Prefer `book_value`** if present (cost basis is more accurate)
2. **Fall back to `market_value`** if `book_value` not present
3. **Error** if neither column exists
4. **Store both** if both columns present (for future market value tracking)

### Example CSV Processing:

**Example 1: market_value Only**
```csv
Ticker,Quantity,Market Value
AAPL-US,100,19000.00
```
→ Uses `market_value` (19000) as `book_value`

**Example 2: book_value Only**
```csv
Ticker,Quantity,Book Value
AAPL-US,100,19000.00
```
→ Uses `book_value` (19000) directly

**Example 3: Both Columns**
```csv
Ticker,Quantity,Book Value,Market Value
AAPL-US,100,19000.00,24000.00
```
→ Uses `book_value` (19000) as primary
→ Stores `market_value` (24000) separately for gain/loss calculation

## Implementation Details

### Smart Handling
- If CSV has `market_value` but not `book_value`, the `market_value` is used as the book_value
- This maintains backward compatibility with old CSV files
- Weights are still calculated correctly based on the value column

### Logging
- Info logs when market_value is used as book_value
- Debug logs show which columns are present
- Error logs clearly show what's missing

### Validation
- Header validation now checks for at least one value column
- Position validation accepts either column
- Clear error messages guide users to correct format

## Migration Path

For users with old CSV format:
```
BEFORE (fails now without fix):
Ticker,Quantity,Market Value
AAPL-US,100,19000.00

AFTER (works with fix):
Ticker,Quantity,Market Value    ← automatically uses as book_value
AAPL-US,100,19000.00

OPTIONAL CONVERSION:
Ticker,Quantity,Book Value       ← preferred new format
AAPL-US,100,19000.00
```

## Backward Compatibility Verification

✓ Old CSVs with `market_value` column load successfully
✓ New CSVs with `book_value` column load successfully
✓ CSVs with both columns work correctly
✓ Column name variations (spaces, case) are handled
✓ All existing tests continue to pass
✓ No breaking changes to API

## Files Modified
1. `src/pagr/fds/loaders/validator.py` - Enhanced to accept either column
2. `src/pagr/fds/loaders/portfolio_loader.py` - Smart value column selection

## Files Created
1. `tests/test_market_value_column.py` - Comprehensive backward compatibility tests

## Next Steps

Users can now:
1. Upload CSVs with `market_value` column (old format)
2. Upload CSVs with `book_value` column (new format)
3. Upload CSVs with both columns
4. Mix column name formats (spaces, underscores, case variations)

No CSV format changes required for existing users - the application now handles both formats automatically.

## Status: COMPLETE ✓
- Implementation: Done
- Testing: 23/23 passing
- Documentation: Complete
- Ready for production: YES
