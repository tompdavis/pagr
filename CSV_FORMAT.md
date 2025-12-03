# Portfolio CSV Format Guide

## Overview

PAGR (Portfolio Analysis Graph Repository) supports portfolio files containing both **stocks** and **bonds**. This guide explains the CSV format and provides examples for different portfolio configurations.

## Required Fields

Every position in your portfolio CSV must have:

1. **quantity** - Number of shares/units (must be > 0)
2. **book_value** - Cost basis in USD (must be ≥ 0)
3. **At least ONE identifier** - ticker OR isin OR cusip

## Optional Fields

- **security_type** - Type of security (e.g., "Common Stock", "Corporate Bond", "Treasury Bond")
- **market_value** - Current market value in USD
- **purchase_date** - Date purchased (YYYY-MM-DD format)

## Identifier Priority

When multiple identifiers are provided, PAGR uses this priority:

1. **CUSIP** (preferred for bonds)
2. **ISIN** (fallback for bonds)
3. **Ticker** (for stocks)

## CSV Format Specification

### Headers (Case-insensitive)

```
ticker,quantity,book_value,security_type,isin,cusip,market_value,purchase_date
```

### Column Details

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| ticker | string | Conditional | Leave blank for bonds. Format: TICKER-EXCHANGE (e.g., AAPL-US) |
| quantity | float | Yes | Must be positive. Can be fractional (e.g., 100.5) |
| book_value | float | Yes | Cost basis in USD. Use 0 for free holdings |
| security_type | string | No | Descriptive only. Examples: Common Stock, Preferred Stock, Corporate Bond, Treasury Bond, Municipal Bond |
| isin | string | Conditional | ISIN identifier. 12-character code. Use only for bonds if CUSIP unavailable |
| cusip | string | Conditional | CUSIP identifier. 9-character code. Preferred for bonds |
| market_value | float | No | Current market value. If not provided, book_value used as fallback |
| purchase_date | string | No | Format: YYYY-MM-DD |

## Valid Values for Missing Data

The following values are treated as "missing" for identifier fields:
- Empty string: `""` or ` `
- N/A: `N/A`, `n/a`, `NA`
- Null: `null`, `NULL`, `Null`

## Example 1: Stock-Only Portfolio

```csv
ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,,
MSFT-US,50,21000.00,Common Stock,,
GOOGL-US,25,3250.00,Common Stock,,
```

## Example 2: Bond-Only Portfolio

```csv
ticker,quantity,book_value,security_type,isin,cusip
,500,50000.00,Corporate Bond,,037833AA5
,300,30000.00,Treasury Bond,US912828Z772,
,200,20000.00,Municipal Bond,US037833AA56,037833AA6
```

## Example 3: Mixed Stock and Bond Portfolio

```csv
ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,,
MSFT-US,50,21000.00,Common Stock,,
,500,50000.00,Corporate Bond,,037833AA5
,300,30000.00,Treasury Bond,US912828Z772,
TSLA-US,25,8000.00,Common Stock,,
,200,20000.00,Municipal Bond,US037833AA56,037833AA6
```

## Example 4: Portfolio with Market Values

```csv
ticker,quantity,book_value,security_type,market_value,purchase_date,isin,cusip
AAPL-US,100,19000.00,Common Stock,22000.00,2023-01-15,,
MSFT-US,50,21000.00,Common Stock,25000.00,2022-06-20,,
,500,50000.00,Corporate Bond,51000.00,2021-03-10,,037833AA5
,300,30000.00,Treasury Bond,31000.00,2024-01-05,US912828Z772,
```

## Best Practices

### 1. Ticker Format for Stocks
- Always include exchange code: `AAPL-US`, `ASML-AS`, `SAP-DE`
- Do not use just ticker: ❌ `AAPL`, ✅ `AAPL-US`

### 2. Bond Identifiers
- **Prefer CUSIP**: If you have both CUSIP and ISIN, CUSIP will be used for pricing
- **ISIN as fallback**: Use ISIN only if CUSIP unavailable
- **Leave ticker blank**: Never fill ticker field for bonds

### 3. Quantities and Values
- Use decimal notation: `100.5` (not `100,5`)
- Use positive numbers: `100` (not `-100`)
- Use currency amounts without $ symbol: `19000.00` (not `$19,000`)

### 4. Security Types
- Stock types: `Common Stock`, `Preferred Stock`, `ETF`
- Bond types: `Corporate Bond`, `Treasury Bond`, `Municipal Bond`, `Government Bond`
- Use descriptive names for clarity in UI

### 5. File Format
- **Encoding**: UTF-8 (with or without BOM)
- **Line endings**: CRLF (Windows) or LF (Unix)
- **Delimiter**: Comma (`,`)
- **Quoted fields**: Quote fields containing commas or newlines

## Common Errors and Solutions

### Error: "Must provide at least one identifier: ticker, isin, or cusip"

**Cause**: Row has no valid identifier in any of the three columns

**Solution**:
```csv
# ❌ Wrong
,100,10000.00,Unknown Asset

# ✅ Correct
AAPL-US,100,10000.00,Common Stock

# ✅ Also correct
,100,10000.00,Corporate Bond,,037833AA5
```

### Error: "Quantity must be positive"

**Cause**: Quantity is negative, zero, or not a number

**Solution**:
```csv
# ❌ Wrong
AAPL-US,-100,10000.00,Common Stock
AAPL-US,0,10000.00,Common Stock
AAPL-US,abc,10000.00,Common Stock

# ✅ Correct
AAPL-US,100,10000.00,Common Stock
AAPL-US,100.5,10000.00,Common Stock
```

### Error: "Must have either 'book_value' or 'market_value'"

**Cause**: Position has neither book_value nor market_value

**Solution**:
```csv
# ❌ Wrong
AAPL-US,100,,Common Stock

# ✅ Correct
AAPL-US,100,10000.00,Common Stock

# ✅ Also correct (with market value)
AAPL-US,100,10000.00,Common Stock,11000.00
```

### Error: "Ticker may be in invalid format"

**Cause**: Stock ticker missing exchange code (warning only, file still uploads)

**Solution**:
```csv
# ⚠️  Warning (but acceptable)
AAPL,100,10000.00,Common Stock

# ✅ Recommended format
AAPL-US,100,10000.00,Common Stock
```

## FactSet Data Enrichment

When you upload a portfolio, PAGR automatically enriches your data with information from FactSet:

### For Stocks
- Company name, sector, country
- Current market price
- Executive information (CEO, CFO, etc.)

### For Bonds
- Coupon rate
- Currency
- Maturity date
- Current market price
- Issuer company information

**Note**: If FactSet data is unavailable for a bond, PAGR will still accept it with "N/A" values. You can view the position but pricing and issuer information may be missing.

## File Upload Tips

1. **Save as CSV**: Use `.csv` file extension
2. **Test first**: Try uploading with a small test portfolio
3. **Backup original**: Keep a copy before uploading
4. **Check encoding**: Ensure UTF-8 encoding if using special characters
5. **Verify dates**: Use YYYY-MM-DD format for any dates

## Support

For issues or questions:
1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review the [Architecture Documentation](ARCHITECTURE.md)
3. Check error messages for specific guidance
