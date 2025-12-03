# Troubleshooting Guide

Quick fixes for common PAGR issues.

## Portfolio Upload Issues

### "Portfolio file not found"

**Check**:
```bash
# Verify file exists in current directory
ls -la my_portfolio.csv

# Or use full path
python -c "import os; print(os.path.exists('/full/path/to/file.csv'))"
```

**Fix**:
```python
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
import os

file_path = "my_portfolio.csv"
if os.path.exists(file_path):
    portfolio = PortfolioLoader.load(file_path)
else:
    print(f"File not found: {file_path}")
    print(f"Current directory: {os.getcwd()}")
```

### "CSV validation failed"

**Check your CSV**:
1. Open in text editor (not Excel - Excel hides formatting)
2. Verify comma separation (not semicolons)
3. Check for hidden spaces or special characters
4. Verify numbers don't have currency symbols

**Fix**:
```bash
# Check encoding
file my_portfolio.csv
# Should show: UTF-8 Unicode text

# View first few lines
head -5 my_portfolio.csv

# Count commas per line (should match header count)
head -1 my_portfolio.csv | tr ',' '\n' | wc -l
```

### "Invalid identifier format"

**Example**: `ticker 'AAPL' may be in invalid format`

**Fix**:
```csv
# ❌ Without exchange
AAPL,100,10000.00,Common Stock

# ✅ With exchange code
AAPL-US,100,10000.00,Common Stock
```

**Common exchange codes**:
- US: `AAPL-US`, `MSFT-US`
- Netherlands: `ASML-AS`, `BRIM-AS`
- Germany: `SAP-DE`, `SIE-DE`
- UK: `HSBA-GB`, `BP-GB`

### "Must provide at least one identifier"

**Check**:
```csv
# All three identifier fields empty/null
ticker,isin,cusip
,,
```

**Fix**:
```csv
# Option 1: Stock with ticker
AAPL-US,
# Option 2: Bond with CUSIP
,,037833AA5
# Option 3: Bond with ISIN
US912828Z772,
```

## FactSet API Issues

### "Authentication failed - invalid credentials"

**Check**:
```bash
echo "Username: $FDS_USERNAME"
echo "API Key: ${FDS_API_KEY:0:10}..." # Don't show full key!
```

**Fix**:
```bash
# 1. Get credentials from FactSet portal
# 2. Set environment variables
export FDS_USERNAME="your-username-serial"
export FDS_API_KEY="your-api-key"

# 3. Verify format
# Username should be: NAME-SERIAL (e.g., john-doe-001)
# API Key should be: 40+ character string
```

### "Rate limit exceeded - retrying..."

**Normal behavior**: Automatic retry happens

**If keeps happening**:
```python
# Upload smaller batches
from pagr.fds.loaders.portfolio_loader import PortfolioLoader

# Split large CSV into smaller files
# Portfolio_1.csv: first 50 positions
# Portfolio_2.csv: next 50 positions

portfolio1 = PortfolioLoader.load("portfolio_1.csv")
portfolio2 = PortfolioLoader.load("portfolio_2.csv")
```

### "Bond not found in FactSet"

**Example**: CUSIP `123456ABC` not in FactSet

**Check**:
1. Verify CUSIP is correct (9 characters)
2. Try ISIN instead (12 characters)
3. Check bond still exists (may have matured/been called)

**Fix**:
```python
from pagr.fds.clients.factset_client import FactSetClient

client = FactSetClient(username=user, api_key=key)

# Test if identifier works
try:
    data = client.get_bond_details("YOUR_CUSIP", id_type="CUSIP")
    print("✓ Bond found")
except Exception as e:
    print(f"✗ Not found: {e}")
    # Try with ISIN
    data = client.get_bond_details("YOUR_ISIN", id_type="ISIN")
```

**Result**: Bond still uploads with "N/A" for price/coupon

## Graph Database Issues

### "Memgraph server not running"

**Check**:
```bash
# List running containers
docker ps | grep memgraph

# Or check if service is running
systemctl status memgraph
```

**Fix**:
```bash
# Start Memgraph with Docker
docker-compose up memgraph

# Or start system service
sudo systemctl start memgraph

# Verify connection
python -c "from gqlalchemy import QueryBuilder; print('✓ Memgraph connected')"
```

### "Graph query timeout"

**Check**: Portfolio size
```python
print(f"Positions: {len(portfolio.positions)}")
print(f"Total value: ${portfolio.total_value:,.2f}")
```

**If very large portfolio** (>10,000 positions):

**Fix**:
```python
# 1. Reduce portfolio size
large_portfolio = PortfolioLoader.load("large.csv")
positions_subset = large_portfolio.positions[:1000]

# 2. Or use sector/country drill-down instead of full view
# (built-in pagination handles this)

# 3. Increase timeout
from pagr.fds.graph.queries import QueryService
query_service = QueryService(graph_client, timeout=60)
```

### "Connection refused: memgraph server"

**Check port**:
```bash
# Default port is 7687
netstat -an | grep 7687

# Or check with lsof
lsof -i :7687
```

**Fix**:
```bash
# Start Memgraph on correct port
docker run -p 7687:7687 memgraph

# Or update connection config
export MEMGRAPH_URI="bolt://localhost:7687"
```

## Portfolio Display Issues

### "No positions to display"

**Check**:
```python
portfolio = PortfolioLoader.load("my_portfolio.csv")
print(f"Positions loaded: {len(portfolio.positions)}")

for pos in portfolio.positions:
    print(f"  {pos.ticker or pos.cusip}: {pos.quantity} units")
```

**Fix**:
1. Verify CSV file is not empty
2. Check CSV has data rows (not just headers)
3. Verify CSV passes validation

### "Some positions missing from display"

**Check**: Error logs
```bash
# Look for warning messages
grep "❌\|⚠️" application.log

# Or check directly
python -c "
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
p = PortfolioLoader.load('file.csv')
print(f'Loaded: {len(p.positions)} positions')
"
```

**Common causes**:
- Invalid identifiers (not showing error but skipped)
- Duplicate positions (deduplicated automatically)
- Encoding issues (special characters corrupted)

### "Sector/Country exposure showing N/A"

**Check**: Graph data
```python
# Test query directly
result = query_service.sector_exposure("Portfolio Name")
print(f"Records: {len(result.records)}")
for record in result.records:
    print(record)
```

**Fix**:
1. Verify portfolio name matches exactly (case-sensitive)
2. Check FactSet enrichment completed (may take time)
3. Try refreshing/reloading view

## Data Quality Issues

### "Market values don't match book values"

**Expected**: Market values may be outdated (from CSV)

**Check**:
```python
for pos in portfolio.positions:
    print(f"Book: ${pos.book_value:.2f}, Market: ${pos.market_value:.2f}")
```

**Note**: PAGR uses whatever market value is in CSV (not fetched from FactSet)

**Solution**: Update market values in CSV periodically

### "Weights don't add up to 100%"

**This is normal**: Due to rounding in UI display

```python
# Calculate exactly
total_value = sum(pos.book_value for pos in portfolio.positions)
for pos in portfolio.positions:
    weight = (pos.book_value / total_value) * 100
    print(f"  {pos.ticker}: {weight:.4f}%")
```

**Weights shown in UI**: Rounded to 2 decimal places

### "Bond coupons showing as N/A"

**Check**: Bond was found in FactSet
```python
from pagr.fds.enrichers.bond_enricher import BondEnricher

enricher = BondEnricher(client)
bond = enricher.enrich_bond(cusip="037833AA5")
print(f"Coupon: {bond.coupon}")
print(f"Currency: {bond.currency}")
```

**Common causes**:
- Bond not in FactSet database
- FactSet API not responding
- Invalid bond identifier

**Solution**:
- Verify bond identifier
- Retry upload
- Position will still work with N/A values

## Performance Issues

### "Slow to load large portfolio"

**Optimization**:
```python
# Batch processing
import time

positions = portfolio.positions
batch_size = 100

for i in range(0, len(positions), batch_size):
    batch = positions[i:i+batch_size]
    print(f"Processing positions {i} to {i+len(batch)}")
    # Process batch
    time.sleep(1)  # Rate limiting
```

### "UI laggy with many positions"

**Solutions**:
1. Use drill-down views (sector/country specific)
2. Limit visible positions (pagination)
3. Close other applications
4. Increase allocated memory

```bash
# Run with more memory
python -Xmx4G app.py

# Or with Docker
docker run -e JAVA_TOOL_OPTIONS="-Xmx4G" memgraph
```

## Reset/Recovery

### "Start fresh with clean database"

```bash
# 1. Stop PAGR
# Ctrl+C in terminal

# 2. Clear Memgraph data
docker-compose down -v
docker-compose up memgraph

# 3. Restart PAGR
python app.py

# 4. Re-upload portfolio
```

### "Reload portfolio without clearing database"

```python
# Clear in-memory cache
import streamlit as st
st.session_state.portfolio = None
st.session_state.graph_built = False

# Re-upload same file
```

### "Backup portfolio data"

```bash
# Export portfolio data
python -c "
from pagr.fds.loaders.portfolio_loader import PortfolioLoader
portfolio = PortfolioLoader.load('portfolio.csv')

# Save as JSON
import json
data = {
    'name': portfolio.name,
    'positions': [
        {
            'ticker': p.ticker,
            'quantity': p.quantity,
            'book_value': p.book_value
        }
        for p in portfolio.positions
    ]
}
with open('portfolio_backup.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

## When All Else Fails

### Checklist

- [ ] Verified CSV file exists and is readable
- [ ] Checked CSV format (UTF-8, comma-separated)
- [ ] Verified all required columns present
- [ ] Checked identifier format (TICKER-EXCHANGE, CUSIP, ISIN)
- [ ] Verified FactSet credentials (export FDS_USERNAME, FDS_API_KEY)
- [ ] Started Memgraph (docker-compose up memgraph)
- [ ] Checked error logs (application.log or console)
- [ ] Tried restarting application
- [ ] Tried with smaller test portfolio

### Collect Debug Information

```bash
# System info
uname -a
python --version

# PAGR version
pip show pagr

# Environment variables
env | grep -E "FDS_|MEMGRAPH_"

# Check services
docker ps
systemctl status memgraph

# Logs
tail -100 application.log
```

### Get Help

1. Share collected debug information
2. Share sample CSV (with sensitive data removed)
3. Share exact error message
4. Describe steps taken to reproduce

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| CSV not loading | Check file exists, verify UTF-8 encoding |
| Auth failed | Check FDS_USERNAME and FDS_API_KEY |
| Rate limited | Wait for automatic retry, or split portfolio |
| Bond not found | Verify CUSIP/ISIN, try ISIN if CUSIP fails |
| Memgraph down | `docker-compose up memgraph` |
| Slow loading | Use drill-down views, reduce batch size |
| No positions | Check CSV has data rows, not just headers |
| Weights off | Normal rounding, calculate exactly if needed |

## Documentation References

- **CSV Format**: [CSV_FORMAT.md](CSV_FORMAT.md)
- **Error Codes**: [ERROR_HANDLING.md](ERROR_HANDLING.md)
- **Migration**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
