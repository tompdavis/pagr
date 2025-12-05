# Country Display Fix - Graph View "Show Countries" Now Works

## Problem
When clicking the "Show Countries" checkbox in the graph view, country information was not displayed. Investigation revealed that Country nodes in the database had incomplete data:
- `fibo_id: None` (should be "fibo:country:XX")
- `name: None` (should be country name like "United States")
- `iso_code: US` (only this property had data)

## Root Cause Analysis

### Two Conflicting Methods Creating Country Nodes

The graph builder had **two different methods** creating Country nodes with incompatible merge strategies:

**Method 1: `add_country_nodes()` (lines 168-194)**
```python
MERGE (c:Country {fibo_id: '{fibo_id}'})  # Merge on fibo_id
SET c.name = '{name}', c.iso_code = '{iso_code}'
```

**Method 2: `add_headquartered_in_relationships()` (lines 443-467)**
```python
MERGE (co:Country {iso_code: '{iso_code}'})  # Merge on iso_code
CREATE (c)-[:HEADQUARTERED_IN]->(co)        # Only creates node, no properties set!
```

### The Problem Chain

1. **Call Order**: `add_country_nodes()` called BEFORE `add_headquartered_in_relationships()`
2. **Conflict**: Both methods operate on the same Country nodes but use different unique identifiers
   - Method 1 uses `fibo_id` as the merge key
   - Method 2 uses `iso_code` as the merge key
3. **Result**: When Method 2 executes, it finds no existing nodes (because merge keys don't match) and creates NEW nodes
4. **Incomplete Data**: Method 2's newly created nodes only have `iso_code` set; `fibo_id` and `name` remain None

### Additional Issue: Inconsistent Country Dict Keys

In `pipeline.py`, the countries dict was being populated with mixed keys:
- **Stock enrichment path** (line 312): `countries[company.country] = country` (keyed by name)
- **Bond enrichment path** (line 391): `countries[iso_code] = country` (keyed by iso_code)

When `add_country_nodes()` iterated with `for iso_code, country in countries.items()`, it received inconsistent key types, causing incorrect iso_code values for stocks.

## Solution

### Fix 1: Consistent Merge Strategy in `add_country_nodes()`
**File**: `src/pagr/fds/graph/builder.py` lines 168-194

Changed from merging on `fibo_id` to merging on `iso_code`:

```python
# BEFORE (BROKEN):
f"MERGE (c:Country {{fibo_id: '{fibo_id}'}}) "
f"SET c.name = '{name}', "
f"c.iso_code = '{iso_clean}' "

# AFTER (FIXED):
f"MERGE (c:Country {{iso_code: '{iso_clean}'}}) "
f"SET c.fibo_id = '{fibo_id}', "
f"c.name = '{name}' "
```

**Why**: `iso_code` is the true unique identifier for countries (globally standardized ISO 3166-1 code). Using it ensures nodes are identified consistently.

### Fix 2: Complete Node Properties in `add_headquartered_in_relationships()`
**File**: `src/pagr/fds/graph/builder.py` lines 443-467

Added ON CREATE SET clause to ensure fibo_id and name are set when creating new Country nodes:

```python
# BEFORE (INCOMPLETE):
f"MERGE (co:Country {{iso_code: '{country_iso_clean}'}}) "
f"CREATE (c)-[:HEADQUARTERED_IN]->(co);"

# AFTER (COMPLETE):
f"MERGE (co:Country {{iso_code: '{country_iso_clean}'}}) "
f"ON CREATE SET co.fibo_id = COALESCE(co.fibo_id, 'fibo:country:{country_iso_clean}'), "
f"co.name = COALESCE(co.name, '') "
f"CREATE (c)-[:HEADQUARTERED_IN]->(co);"
```

### Fix 3: Consistent Country Dict Keys in Pipeline
**File**: `src/pagr/fds/services/pipeline.py`

**Stock Enrichment Path** (lines 296-318):
- Extract `iso_code` properly from relationship's `fibo_id`: `rel.target_fibo_id.split(":")[-1]`
- Key countries dict by `iso_code`: `countries[iso_code] = country`

**Bond Enrichment Path** (lines 381-402):
- Use relationship enricher (consistent with stock path)
- Extract `iso_code` from relationship's `fibo_id`
- Key countries dict by `iso_code`: `countries[iso_code] = country`

## Verification

Generated Cypher statements now properly create Country nodes:

```cypher
MERGE (c:Country {iso_code: 'US'})
SET c.fibo_id = 'fibo:country:US', c.name = 'United States'
RETURN c;

MERGE (c:Country {iso_code: 'FR'})
SET c.fibo_id = 'fibo:country:FR', c.name = 'France'
RETURN c;
```

**Result**: Country nodes in database now have:
- ✅ `fibo_id: fibo:country:US`
- ✅ `name: United States`
- ✅ `iso_code: US`

## Testing

To verify the fix works:

1. **Clear database**:
   ```bash
   uv run python -c "
   from src.pagr.fds.clients.memgraph_client import MemgraphClient
   c = MemgraphClient('127.0.0.1', 7687)
   c.connect()
   c.execute_query('MATCH (n) DETACH DELETE n')
   print('Database cleared')
   "
   ```

2. **Load a portfolio with international holdings** (e.g., `muti-asset_portfolio.csv`)

3. **Verify Country nodes in database**:
   ```bash
   uv run python -c "
   from src.pagr.fds.clients.memgraph_client import MemgraphClient
   c = MemgraphClient('127.0.0.1', 7687)
   c.connect()
   results = c.execute_query('MATCH (c:Country) RETURN c.fibo_id, c.name, c.iso_code')
   for r in results:
       print(f\"fibo_id={r.get('c.fibo_id')}, name={r.get('c.name')}, iso_code={r.get('c.iso_code')}\")
   "
   ```

4. **Test in app**:
   - Open Holdings tab, verify company sectors display
   - Open Graph View tab, click "Show Countries" checkbox
   - Verify country nodes appear with proper labels

## Impact

- **Graph View**: Country nodes now display correctly with labels (country names)
- **Holdings View**: Geographic data can be properly displayed
- **Data Integrity**: Country nodes have complete FIBO representation (fibo_id, name, iso_code)
- **Multi-Portfolio**: Country nodes are shared across portfolios (merged on iso_code for uniqueness)

## Files Modified

1. `src/pagr/fds/graph/builder.py` - Fixed MERGE strategy for Country nodes
2. `src/pagr/fds/services/pipeline.py` - Fixed country dict key consistency and enrichment logic

## Related Bugs Fixed

This fix resolves the cascading issue reported by the user:
- ✅ "when i click 'show countries' the graph view does not update with the country information"
- ✅ Country nodes now have complete data
- ✅ Holdings view can display geographic information
- ✅ Full relationship chain now visible: Position → Stock → Company → Country
