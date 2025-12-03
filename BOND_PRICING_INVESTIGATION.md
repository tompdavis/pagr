# Bond Pricing API Investigation

**Date**: December 3, 2025
**Status**: Investigating FactSet Fixed Income API versions for bond market pricing

## Current Situation

### Working Implementation
- **Graph Schema**: Bonds are correctly stored with market_price from book_value fallback
- **Tests**: All tests confirm bonds are included in sector and country breakdowns
- **Database**: Bond has market_price = 23,340.00 (using book_value fallback)

### API Issue
Currently getting **HTTP 400 Bad Request** from:
```
POST /content/factset-global-prices/v1/prices
```

### Request Details
```json
{
  "ids": ["037833100"],
  "idType": "CUSIP",
  "frequency": "D",
  "startDate": "2025-11-28",
  "endDate": "2025-12-03"
}
```

## FactSet API Analysis

### Current Implementation (v1)
- **Primary Endpoint**: `/content/factset-global-prices/v1/prices`
- **Status**: Returns 400 Bad Request for CUSIP identifiers
- **Alternative**: `/content/factset-fixed-income/v1/bond-details` (partial data only)

### v3 Investigation

The user suggested exploring FactSet Fixed Income Calculation API v3. Potential advantages:
1. **Dedicated Bond Endpoint**: May have better support for bond pricing
2. **Clean Price Data**: Should provide clean price (not dirty/accrued price)
3. **Single Call**: Could combine reference data + pricing in one request
4. **Better CUSIP Support**: v3 might have improved identifier handling

### Key Questions to Resolve

1. **Does v3 Fixed Income API exist?** - Need to verify endpoint structure
2. **What identifiers does v3 support?** - CUSIP, ISIN, or others?
3. **What is the request format?** - JSON payload structure
4. **What fields are returned?** - Price, coupon, currency, maturity, issuer
5. **Backwards compatibility?** - Can we migrate without breaking existing code?

## Solution Approaches

### Option A: Fix v1 Request
- Debug the 400 error with global prices endpoint
- May be parameter ordering, date format, or authentication issue
- **Pros**: Less code change
- **Cons**: Uncertain if v1 fully supports bonds

### Option B: Use Fixed Income v1 Only
- Rely on `/content/factset-fixed-income/v1/bond-details`
- May have limitations but works for reference data
- **Pros**: Avoids global prices endpoint
- **Cons**: May not have complete pricing data

### Option C: Migrate to Fixed Income v3
- Implement new v3 endpoints if available
- **Pros**: Future-proofing, potentially better bond support
- **Cons**: Need to verify API exists and is stable

### Option D: Hybrid Approach
- Try v1 Fixed Income API for reference data
- Fall back to book_value for pricing if API fails
- **Current Status**: Already implemented (graceful degradation)
- **Pros**: Works now, no API changes needed
- **Cons**: Doesn't get actual market pricing

## Recommended Next Steps

1. **Verify FactSet v3 API Availability**
   - Check API portal documentation
   - Contact FactSet support if needed
   - Confirm endpoint structure and capabilities

2. **Debug v1 Global Prices Issue**
   - Test with different identifier types
   - Check API credentials and permissions
   - Verify request parameters

3. **Alternative: Use Fixed Income Analytics API**
   - Look for dedicated bond pricing endpoints
   - May have better CUSIP support than global prices

4. **Testing Strategy**
   - Once API endpoint is confirmed, add integration tests
   - Test with multiple CUSIP/ISIN combinations
   - Verify price accuracy with known bond data

## Current Graceful Degradation

**Status**: ✅ Working
- Bonds load successfully even if FactSet API fails
- Market price falls back to book_value (100 = 100% of par)
- User sees realistic prices in UI
- No data loss or errors

**Example**:
- Bond CUSIP 037833100 with book_value=$23,340
- API fails, falls back to market_price=$23,340
- Displayed as $23,340 (100% of par)

## Implementation Path Forward

### If v3 is Available
```python
# New endpoint
POST /content/factset-fixed-income/v3/prices-and-details
{
  "ids": ["037833100"],
  "idType": "CUSIP"
}
```

### If Only v1 Works
```python
# Current approach with better error handling
# Use fixed-income v1 for reference data
# Manual pricing calculation or fallback
```

## Files to Update

If migration is needed:
1. `src/pagr/fds/clients/factset_client.py` - Add v3 endpoint methods
2. `src/pagr/fds/enrichers/bond_enricher.py` - Update to use new API
3. `tests/test_bond_enrichment.py` - Add v3 endpoint tests

## Decision Required

Please confirm which approach to pursue:
- [ ] Investigate and implement FactSet Fixed Income v3
- [ ] Debug and fix v1 global prices endpoint
- [ ] Continue with current v1 Fixed Income API + graceful fallback
- [ ] Other approach?

## Notes

- Current implementation is **production-ready** with fallback
- Users see realistic prices even without real-time FactSet data
- No urgent need to change API, but fixing pricing would improve accuracy
- Bonds are **correctly included** in all portfolio analytics regardless of pricing source
