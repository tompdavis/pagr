# Implementation Plan: Add Bond Support to PAGR Portfolio Dashboard

## Overview
Add Fixed Coupon Bonds as a new asset class to the portfolio dashboard, refactoring the security model to support multiple instrument types through a clean graph hierarchy.

## User Requirements Summary
- **New Asset Class:** Fixed Coupon Bonds (ISIN or CUSIP identifier, no ticker)
- **Bond Attributes:** issuer (Company), currency, coupon rate, market price (clean price)
- **Bond Enrichment:** Fetch coupon, currency, issuer from FactSet (NOT from CSV)
- **Graph Refactor:** Position → INVESTED_IN → Security → ISSUED_BY → Company
- **CSV Format:** Make ticker optional, require ticker OR isin OR cusip (any one)
- **UI Changes:** "Ticker" → "Security Description" (show ticker for stocks, CUSIP for bonds)
- **Pricing:** Fetch bond prices via FactSet Fixed Income API using CUSIP (prefer) or ISIN

## Design Decisions
1. **CSV Validation:** Require ticker OR isin OR cusip (at least one identifier)
2. **Identifier Priority:** CUSIP > ISIN when both provided (always prefer CUSIP)
3. **Bond Data Source:** FactSet Fixed Income Prices & Analytics API (coupon, currency, price)
4. **Missing Bond Data:** Allow bonds with N/A values if enrichment returns incomplete data
5. **CSV Columns:** Keep separate ticker, isin, cusip columns (NOT combined)
6. **Graph Schema:** Position → Security → Company (clean hierarchy, remove direct Position→Company)
7. **Security Type:** Flexible validation with warnings (allow future types)

## Implementation Phases

### Phase 1: Data Model Foundation
**Files:** `portfolio.py`, `fibo.py`

**Changes:**
1. Make `ticker: Optional[str]` in Position model
2. **Do NOT add coupon/currency to Position** - these are enriched from FactSet
3. Add validation: require ticker OR isin OR cusip (at least one)
4. Update Bond FIBO model: add coupon, currency, market_price (populated during enrichment)
5. Update Stock FIBO model: add market_price
6. Create helper to determine security type and get primary identifier (CUSIP > ISIN > ticker)

**Key Code:**
```python
class Position(BaseModel):
    ticker: Optional[str] = None  # Optional for bonds
    quantity: float = Field(gt=0)
    book_value: float = Field(ge=0)
    security_type: str = "Common Stock"
    isin: Optional[str] = None
    cusip: Optional[str] = None
    # NOTE: coupon and currency NOT here - fetched during enrichment

    @model_validator(mode='after')
    def validate_identifiers(self):
        if not any([self.ticker, self.isin, self.cusip]):
            raise ValueError("Must provide at least one identifier: ticker, isin, or cusip")
        return self

    def get_primary_identifier(self) -> tuple[str, str]:
        """Returns (id_type, id_value) preferring CUSIP > ISIN > ticker."""
        if self.cusip:
            return ("cusip", self.cusip)
        elif self.isin:
            return ("isin", self.isin)
        elif self.ticker:
            return ("ticker", self.ticker)
        return (None, None)
```

### Phase 2: CSV Loading & Validation
**Files:** `validator.py`, `portfolio_loader.py`

**Changes:**
1. Remove ticker from REQUIRED_COLUMNS
2. Add identifier validation: ticker OR isin OR cusip (at least one)
3. Handle N/A, null, empty string for all identifier fields
4. **Remove coupon and currency columns** - not needed in CSV (enriched from FactSet)
5. Accept any security_type value, warn if unrecognized
6. Create sample CSV with mixed stocks and bonds

**Validation Logic:**
```python
REQUIRED_COLUMNS = {"quantity", "book_value"}
IDENTIFIER_COLUMNS = {"ticker", "isin", "cusip"}

def validate_identifiers(row):
    has_ticker = row.get("ticker") and row["ticker"] not in ["N/A", "null", ""]
    has_isin = row.get("isin") and row["isin"] not in ["N/A", "null", ""]
    has_cusip = row.get("cusip") and row["cusip"] not in ["N/A", "null", ""]

    if not (has_ticker or has_isin or has_cusip):
        raise ValidationError("Must provide at least one identifier: ticker, isin, or cusip")

def get_primary_identifier(row):
    """Returns (identifier_type, identifier_value) preferring CUSIP > ISIN > ticker."""
    if row.get("cusip") and row["cusip"] not in ["N/A", "null", ""]:
        return ("cusip", row["cusip"])
    elif row.get("isin") and row["isin"] not in ["N/A", "null", ""]:
        return ("isin", row["isin"])
    elif row.get("ticker") and row["ticker"] not in ["N/A", "null", ""]:
        return ("ticker", row["ticker"])
    return (None, None)
```

### Phase 3: FactSet Client Enhancement
**Files:** `factset_client.py`, `bond_enricher.py` (NEW)

**Changes:**
1. Add `get_bond_data(identifier, id_type="CUSIP")` method that returns price, coupon, currency, issuer
2. **Always prefer CUSIP over ISIN** when both available
3. Create new BondEnricher class:
   - `enrich_bond(cusip=None, isin=None)` → Bond FIBO entity with all data
   - `get_bond_details(identifier, id_type)` → dict with price, coupon, currency, issuer
   - Handles missing data gracefully (allows N/A values)
4. Update CompanyEnricher to support both ticker and bond identifier lookup

**API Endpoints:**
- **Primary:** FactSet Fixed Income Prices & Analytics API
  - Returns: clean price, coupon, currency, maturity, issuer in single call
  - Identifier types: CUSIP (preferred), ISIN (fallback)
- **Fallback:** Separate calls if combined endpoint unavailable:
  - Bond prices: `/content/factset-global-prices/v1/prices`
  - Bond reference data: `/content/factset-fixed-income/v1/bond-details`

**Error Handling:**
- If coupon/currency unavailable → Set to "N/A", continue processing
- If issuer unavailable → Create placeholder Company, log warning
- If price unavailable → Use book_value, warn user

### Phase 4: Graph Schema Migration
**Files:** `schema.py`, `builder.py`

**Changes:**
1. Add `INVESTED_IN` relationship type (Position → Security)
2. Keep `ISSUED_BY` relationship type (Security → Company)
3. Remove direct `Position ISSUED_BY Company` relationship
4. Update Stock node properties: add market_price
5. Update Bond node properties: add coupon, currency, market_price
6. Add builder methods:
   - `add_stock_nodes(stocks: Dict[str, Stock])`
   - `add_bond_nodes(bonds: Dict[str, Bond])`
   - `add_invested_in_relationships(position_to_security)`
   - `add_security_issued_by_relationships(security_to_company)`

**New Graph Schema:**
```
Portfolio --CONTAINS--> Position --INVESTED_IN--> Stock/Bond --ISSUED_BY--> Company --HEADQUARTERED_IN--> Country
```

**Migration Strategy:** Clear database on first upload (no backward compatibility)

### Phase 5: ETL Pipeline Updates
**Files:** `pipeline.py`

**Changes:**
1. Update `enrich_positions()` to return stocks and bonds separately
2. Handle mixed portfolios:
   - If `position.ticker`: enrich as stock (existing flow)
   - If `position.isin/cusip`: enrich as bond (new flow via BondEnricher)
3. Update `enrich_prices()`:
   - Split positions into stocks and bonds
   - Fetch stock prices by ticker (existing)
   - Fetch bond prices by ISIN (new)
4. Update `build_graph()`:
   - Create Stock/Bond nodes
   - Create INVESTED_IN relationships (Position → Security)
   - Create ISSUED_BY relationships (Security → Company)

**Key Logic:**
```python
for position in positions:
    if position.ticker:
        # Stock enrichment
        company = company_enricher.enrich_company_by_ticker(position.ticker)
        stock = Stock(fibo_id=f"fibo:stock:{position.ticker}", ticker=position.ticker)
        stocks[position.ticker] = stock
    else:
        # Bond enrichment
        bond = bond_enricher.enrich_bond(position.isin, position.cusip)
        company = bond_enricher.resolve_issuer(position.isin, position.cusip)
        bond.market_price = bond_enricher.get_bond_price(position.isin, position.cusip)
        bonds[position.isin] = bond
```

### Phase 6: Query Updates
**Files:** `queries.py`

**Changes:**
1. Add `INVESTED_IN` hop to all queries:
   - `sector_exposure`: `Position -[:INVESTED_IN]-> Security -[:ISSUED_BY]-> Company`
   - `country_breakdown`: `Position -[:INVESTED_IN]-> Security -[:ISSUED_BY]-> Company`
   - `sector_positions`: Return security details
   - `country_positions`: Return security details
2. Update return fields to include security type and identifier
3. Add new query: `portfolio_securities()` to get all securities with details

**Updated Query Example:**
```cypher
MATCH (p:Portfolio {name: '{portfolio_name}'})-[:CONTAINS]->(pos:Position)
      -[:INVESTED_IN]->(sec)  # sec can be Stock or Bond
      -[:ISSUED_BY]->(c:Company)
RETURN
    c.sector AS sector,
    SUM(pos.market_value) AS total_exposure,
    SUM(pos.weight) AS total_weight,
    COUNT(pos) AS num_positions
ORDER BY total_exposure DESC;
```

### Phase 7: UI Updates
**Files:** `tabular.py`

**Changes:**
1. Change column name: "Ticker" → "Security Description"
2. Update display logic:
   - For stocks: show ticker
   - For bonds: show CUSIP (preferred) or ISIN with "(Bond)" label
3. Add "Type" column to position tables
4. Update sector/country drill-down tables to show security details

**Display Logic:**
```python
for pos in portfolio.positions:
    if pos.ticker:
        security_desc = pos.ticker
    elif pos.cusip:
        security_desc = f"{pos.cusip} (Bond)"
    elif pos.isin:
        security_desc = f"{pos.isin} (Bond)"
    else:
        security_desc = "Unknown"

    positions_data.append({
        "Security": security_desc,  # Changed from "Ticker"
        "Type": pos.security_type,
        "Quantity": pos.quantity,
        "Book Value": f"${pos.book_value:,.2f}",
        "Market Value": f"${pos.market_value:,.2f}" if pos.market_value else "N/A",
        "Weight (%)": f"{pos.weight:.2f}%" if pos.weight else "N/A",
    })
```

### Phase 8: Testing Strategy

**Unit Tests:**
- Position validation with ticker only
- Position validation with ISIN/CUSIP only
- Position validation with neither (should fail)
- Bond enrichment logic
- Bond price fetching

**Integration Tests:**
```csv
# test_mixed_portfolio.csv
Ticker,Quantity,Book Value,Security Type,ISIN,CUSIP
AAPL-US,100,19000.00,Common Stock,,
MSFT-US,50,21000.00,Common Stock,,
,500,50000.00,Corporate Bond,,037833AA5
,300,30000.00,Treasury Bond,US912828Z772,
```
Note: Coupon and currency will be enriched from FactSet during processing

**Graph Query Tests:**
- Verify sector_exposure includes bonds
- Verify country_breakdown includes bonds under issuer country
- Verify position details show correct security identifier

**UI Tests:**
- Upload mixed portfolio
- Verify "Security" column displays correctly
- Verify sector drill-down includes bonds
- Verify market values calculated correctly for bonds

### Phase 9: Error Handling

**Validation Errors:**
- Position with neither ticker nor ISIN/CUSIP → Clear error message
- Bond missing coupon → Warn but continue
- Bond missing currency → Warn, default to USD

**Enrichment Errors:**
- Bond issuer not found → Log error, create placeholder Company
- Bond price not available → Set market_value to book_value, warn user
- ISIN not recognized → Skip enrichment, show warning in UI

**Query Errors:**
- Old schema data detected → Show "Re-upload portfolio to use new schema"
- Missing Security nodes → Detect and prompt re-upload

### Phase 10: Documentation

**CSV Format Documentation:**
```markdown
# Portfolio CSV Format (v2.0)

## Required Fields:
- quantity: Number of shares/units (must be > 0)
- book_value: Cost basis in USD (must be >= 0)
- At least ONE identifier: ticker OR isin OR cusip

## For Stocks:
ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,,
MSFT-US,50,21000.00,Common Stock,,

## For Bonds:
ticker,quantity,book_value,security_type,isin,cusip
,500,50000.00,Corporate Bond,,037833AA5
,300,30000.00,Treasury Bond,US912828Z772,

## Notes:
- Coupon and currency are NOT required in CSV - they are fetched automatically from FactSet
- Prefer CUSIP for bonds when available (CUSIP > ISIN in priority)
- security_type is informational only (system determines type from identifiers)
- Leave unused identifier columns empty or omit them
```

**Migration Guide:**
1. Back up existing portfolios
2. Update PAGR to new version
3. Database will be cleared on first upload
4. Re-upload portfolios with updated CSV format
5. Bonds can now be included

## Implementation Order

1. Phase 1 (Data Models) - Foundation
2. Phase 2 (CSV/Validation) - Input handling
3. Phase 3 (FactSet Client) - API integration
4. Phase 4 (Graph Schema) - Database structure
5. Phase 5 (ETL Pipeline) - Orchestration
6. Phase 6 (Queries) - Data retrieval
7. Phase 7 (UI) - Display layer
8. Phase 8 (Testing) - Validation
9. Phase 9 (Error Handling) - Robustness
10. Phase 10 (Documentation) - User guidance

## Critical Files to Modify

1. `C:\Users\todavis\code\pagr\src\pagr\fds\models\portfolio.py` - Position model
2. `C:\Users\todavis\code\pagr\src\pagr\fds\graph\builder.py` - Graph structure
3. `C:\Users\todavis\code\pagr\src\pagr\fds\services\pipeline.py` - ETL orchestration
4. `C:\Users\todavis\code\pagr\src\pagr\fds\graph\queries.py` - Query updates
5. `C:\Users\todavis\code\pagr\src\pagr\fds\loaders\validator.py` - Validation logic
6. `C:\Users\todavis\code\pagr\src\pagr\fds\clients\factset_client.py` - Bond API
7. `C:\Users\todavis\code\pagr\src\pagr\ui\tabular.py` - Display logic
8. `C:\Users\todavis\code\pagr\src\pagr\fds\graph\schema.py` - Node/relationship types

## Risk Mitigation

**High Risk:**
1. **FactSet API:** Test bond pricing endpoint early with sample ISINs
2. **Graph Migration:** Clear database strategy avoids dual-schema complexity
3. **Bond Issuer Resolution:** Create placeholder Company if lookup fails

**Medium Risk:**
1. **CSV Validation:** Provide clear error messages and sample CSVs
2. **Performance:** Additional graph hop may slow queries 10-20% (acceptable)
3. **Missing Bond Data:** Make coupon/currency optional, show "N/A" in UI

## Success Criteria

- [ ] Upload CSV with mixed stocks and bonds successfully
- [ ] Bond prices fetched from FactSet API
- [ ] Bond issuers resolved to companies
- [ ] Sector exposure includes bonds grouped by issuer sector
- [ ] Country breakdown includes bonds grouped by issuer country
- [ ] UI displays ISINs for bonds, tickers for stocks
- [ ] All existing stock functionality continues to work
- [ ] Clear error messages for invalid CSVs
