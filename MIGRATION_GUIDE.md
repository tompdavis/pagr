# Migration Guide: PAGR v1.0 to v2.0

## Overview

PAGR v2.0 introduces support for **Fixed Coupon Bonds** alongside existing stock portfolios. This guide helps you migrate from v1.0 to v2.0.

## What's New in v2.0

### Major Features
- ✅ **Bond Support**: Add bonds (corporate, treasury, municipal) to portfolios
- ✅ **Flexible Identifiers**: Ticker is now optional; use ISIN or CUSIP for bonds
- ✅ **Automatic Bond Enrichment**: Fetch coupon, currency, and prices from FactSet
- ✅ **Enhanced Graph Schema**: New relationship structure for mixed asset types
- ✅ **Better Error Handling**: Comprehensive error messages and recovery
- ✅ **Improved UI**: "Security" column displays both tickers (stocks) and identifiers (bonds)

### Breaking Changes

1. **Graph Database Reset**: v2.0 uses a new graph schema
   - Old portfolio graphs will not be accessible
   - You must re-upload portfolios after upgrading

2. **Ticker is Optional**: CSV files no longer require `ticker` column
   - For stocks: provide ticker
   - For bonds: provide ISIN or CUSIP (ticker field can be empty)

3. **New CSV Format**: Support for three identifier columns
   - `ticker` (for stocks)
   - `isin` (for bonds - fallback)
   - `cusip` (for bonds - preferred)

## Pre-Migration Checklist

Before upgrading to v2.0:

- [ ] Back up existing portfolio files
- [ ] Backup graph database data (if needed for records)
- [ ] Note any custom portfolio names you want to keep
- [ ] Prepare bond data if adding bonds to your portfolio
- [ ] Test upgrade in a separate environment if possible

## Step-by-Step Migration

### 1. Backup Your Current Setup

```bash
# Backup portfolio CSVs
mkdir backup_v1.0
cp *.csv backup_v1.0/

# Backup any configuration files
cp config/* backup_v1.0/
```

### 2. Install v2.0

```bash
# Update to v2.0
pip install pagr==2.0.0

# Or using uv:
uv pip install pagr==2.0.0
```

### 3. Migrate Your Portfolio CSV

#### Option A: Stock-Only Portfolio (No Changes Needed)

If your v1.0 portfolio contains **only stocks**, the CSV format remains compatible:

```csv
# v1.0 format (still works in v2.0)
ticker,quantity,book_value,security_type
AAPL-US,100,19000.00,Common Stock
MSFT-US,50,21000.00,Common Stock
```

**Action**: No changes required. Upload the same file.

#### Option B: Adding Bonds to Existing Stock Portfolio

If you're adding bonds, add three new columns to your CSV:

```csv
# v2.0 format with bond support
ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,,
MSFT-US,50,21000.00,Common Stock,,
,500,50000.00,Corporate Bond,,037833AA5
,300,30000.00,Treasury Bond,US912828Z772,
```

**Key points**:
- Leave `ticker` blank for bonds (use empty string or space)
- Provide either `isin` or `cusip` for bonds
- CUSIP is preferred if both available

#### Option C: Upgrading from Older CSV Format

If your v1.0 format is missing optional columns, add them:

```csv
# Old v1.0 format (columns may be missing)
ticker,quantity,book_value

# New v2.0 format (add these columns)
ticker,quantity,book_value,security_type,isin,cusip
```

### 4. Prepare Bond Data

If adding bonds, gather bond information:

| Bond Info | Column | Source |
|-----------|--------|--------|
| Identifier | CUSIP or ISIN | Bond prospectus, broker statement |
| Quantity | quantity | Your holdings |
| Cost basis | book_value | Purchase cost or accounting records |
| Bond type | security_type | Classification (Corporate, Treasury, Municipal) |

**Example sources**:
- **Corporate Bonds**: Broker statement, bond trading platform
- **Treasury Bonds**: TreasuryDirect, broker statement
- **Municipal Bonds**: MSRB EMMA database, broker statement

### 5. Upload Updated Portfolio in v2.0

```python
from pagr.fds.loaders.portfolio_loader import PortfolioLoader

# Load updated portfolio
portfolio = PortfolioLoader.load(
    "my_portfolio_v2.csv",
    portfolio_name="My Portfolio"
)

print(f"Loaded {len(portfolio.positions)} positions")
print(f"- Stocks: {len([p for p in portfolio.positions if p.ticker])}")
print(f"- Bonds: {len([p for p in portfolio.positions if not p.ticker])}")
```

### 6. Rebuild Graph Database

```python
from pagr.fds.services.pipeline import ETLPipeline
from pagr.fds.clients.factset_client import FactSetClient
from pagr.fds.loaders.portfolio_loader import PortfolioLoader

# Initialize pipeline
client = FactSetClient(username="YOUR_USERNAME", api_key="YOUR_API_KEY")
loader = PortfolioLoader()
pipeline = ETLPipeline(client, loader)

# Process portfolio (replaces old graph)
portfolio = loader.load("my_portfolio_v2.csv")
stats = pipeline.execute(portfolio)

print(f"✓ Processed {stats.positions_loaded} positions")
print(f"✓ Created {stats.graph_nodes_created} graph nodes")
```

### 7. Verify Migration

```python
# Check that portfolio loaded correctly
print(f"Total value: ${portfolio.total_value:,.2f}")
print(f"Positions: {len(portfolio.positions)}")

# Verify mixed holdings
for pos in portfolio.positions:
    identifier = pos.ticker or f"{pos.cusip or pos.isin} (Bond)"
    print(f"  {identifier}: {pos.quantity} units @ ${pos.book_value:,.2f}")
```

## CSV Format Changes Summary

### v1.0 Format
```csv
ticker,quantity,book_value,security_type
```

### v2.0 Format
```csv
ticker,quantity,book_value,security_type,isin,cusip
```

### Key Differences
| Feature | v1.0 | v2.0 |
|---------|------|------|
| Ticker required | Yes ✓ | Optional (for stocks) |
| ISIN support | No | Yes ✓ |
| CUSIP support | No | Yes ✓ |
| Bonds supported | No | Yes ✓ |
| Bond enrichment | N/A | Yes ✓ |

## Troubleshooting Migration Issues

### Issue: "Old portfolio data not found"

**Cause**: Graph database schema changed between v1.0 and v2.0

**Solution**: This is expected behavior. Re-upload your portfolio with the updated CSV format.

```bash
# Old graphs not accessible - start fresh
# 1. Prepare updated CSV with v2.0 format
# 2. Upload new portfolio
# 3. New graph will be created with v2.0 schema
```

### Issue: "Invalid ticker format" warning

**Cause**: Stock ticker missing exchange code (e.g., `AAPL` instead of `AAPL-US`)

**Solution**: Add exchange code to tickers:

```csv
# ❌ Wrong
AAPL,100,10000.00,Common Stock

# ✅ Correct
AAPL-US,100,10000.00,Common Stock
```

### Issue: "Must provide at least one identifier"

**Cause**: Position has no ticker, ISIN, or CUSIP

**Solution**: Ensure each row has at least one identifier:

```csv
# ❌ Wrong - no identifiers
,100,10000.00,Bond

# ✅ Correct - has CUSIP
,100,10000.00,Corporate Bond,,037833AA5
```

### Issue: "Bond not found in FactSet"

**Cause**: CUSIP/ISIN not recognized by FactSet

**Solution**:
1. Verify bond identifier is correct
2. Position will still upload with "N/A" values
3. Try alternative identifier format

### Issue: "FactSet API authentication failed"

**Cause**: Invalid credentials or API key expired

**Solution**:
1. Check FDS_USERNAME and FDS_API_KEY environment variables
2. Verify credentials in FactSet portal
3. Regenerate API key if needed

## Rollback Procedure

If you need to revert to v1.0:

```bash
# Uninstall v2.0
pip uninstall pagr

# Install v1.0
pip install pagr==1.0.0

# Use backed-up CSV files
cp backup_v1.0/*.csv .
```

**Note**: v1.0 portfolio graphs cannot be accessed from v2.0 data, but your original CSV files remain unchanged.

## FAQ

### Q: Do I need to update all my portfolios?

**A**: Only if you want to use v2.0 features like bonds. v2.0 is backward compatible for stock-only portfolios.

### Q: Will my existing queries work in v2.0?

**A**: Yes, all existing query types work with mixed portfolios. Results now include bonds.

### Q: Can I mix v1.0 and v2.0 portfolios?

**A**: No, the graph database is specific to each version. Recommend upgrading all portfolios at once.

### Q: How do I add bonds to an existing portfolio?

**A**:
1. Update your CSV with bond rows (see "Option B" above)
2. Provide CUSIP or ISIN for each bond
3. Re-upload the updated portfolio

### Q: What if I don't have CUSIP for a bond?

**A**: Use ISIN instead. ISIN is an acceptable fallback.

### Q: Will FactSet enrichment work for all bonds?

**A**: Most bonds should work, but some may not be found in FactSet. These will still load with "N/A" values.

## Support & Resources

- **CSV Format Guide**: See [CSV_FORMAT.md](CSV_FORMAT.md)
- **Error Handling**: See [ERROR_HANDLING.md](ERROR_HANDLING.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Summary

| Step | Action |
|------|--------|
| 1 | Back up current setup |
| 2 | Install v2.0 |
| 3 | Update CSV format (add isin, cusip columns) |
| 4 | Prepare bond data if adding bonds |
| 5 | Upload portfolio with new CSV |
| 6 | Verify migration successful |
| 7 | Reference documentation as needed |

**Migration is complete when**: Your portfolio loads successfully in v2.0 with all positions (stocks and bonds if applicable) displaying correctly in the UI.
