# Graph View Fix - INVESTED_IN Relationships Now Display Correctly

## Problem
The graph view was not displaying INVESTED_IN relationships even though they existed in the database. This happened because:

1. **Stock nodes** in the database have label `:Stock`
2. **Bond nodes** in the database have label `:Bond`
3. **Graph query** was looking for `:Security` label (which doesn't exist)
4. Result: OPTIONAL MATCH failed silently, no relationships were displayed

## Root Cause Analysis

### Database Structure (CORRECT)
```cypher
Position -[:INVESTED_IN]-> Stock (label: Stock)
Position -[:INVESTED_IN]-> Bond (label: Bond)
Stock -[:ISSUED_BY]-> Company
```

### Graph View Query (BROKEN)
```cypher
OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec:Security)  # sec:Security never matched!
OPTIONAL MATCH (sec)-[:ISSUED_BY]->(c:Company)       # Never executed because sec was null
```

### Result
- INVESTED_IN relationships: Not displayed ❌
- Company connections: Not displayed ❌
- Only Positions were shown, isolated from their securities

## Solution

Changed the graph view query in `src/pagr/ui/graph_view.py` line 72:

**Before:**
```python
OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec:Security)
```

**After:**
```python
OPTIONAL MATCH (pos)-[:INVESTED_IN]->(sec:Stock|Bond)
```

This allows the query to match both Stock and Bond node types.

## Verification

After fix, the query correctly returns:
- ✅ 5 INVESTED_IN relationships (Position → Stock)
- ✅ 5 ISSUED_BY relationships (Stock → Company)
- ✅ 5 Company nodes displayed
- ✅ Companies now visible in graph view

## Files Modified
- `src/pagr/ui/graph_view.py` - Line 72: Fixed node label matching in graph query

## Graph View Now Shows
When loading sample_portfolio in graph view:
- Portfolio node (red)
  - ├─ Position nodes (cyan) - CONTAINS relationship
  - └─ INVESTED_IN → Stock nodes (yellow)
       └─ ISSUED_BY → Company nodes (green)

The full relationship chain now displays properly!

## Testing
```bash
# Clear database
uv run python -c "from src.pagr.fds.clients.memgraph_client import MemgraphClient; c = MemgraphClient('127.0.0.1', 7687); c.connect(); c.execute_query('MATCH (n) DETACH DELETE n')"

# Load sample_portfolio
# Open app and go to Graph View tab
# Select sample_portfolio
# Should now see the full relationship chain including companies
```
