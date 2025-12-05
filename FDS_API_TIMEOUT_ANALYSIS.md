# FDS API Timeout Investigation

## Summary
The 10-hour timeout is NOT a bug in your code - it's **expected behavior** based on how the FactSet API implements rate limiting. However, it's a **design issue** that should be addressed.

## Root Cause

### How Rate Limiting Works
1. Your FactSet client (`src/pagr/fds/clients/factset_client.py:125-133`) checks for HTTP 429 (Too Many Requests) status
2. When 429 is received, it reads the `Retry-After` header from the response
3. It then **sleeps for the entire duration** specified in the header before retrying

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 5))
    logger.warning(
        f"Rate limited. Waiting {retry_after} seconds before retry..."
    )
    time.sleep(retry_after)  # <-- BLOCKING SLEEP
```

### Why 10 Hours?
The FactSet API can return `Retry-After: 36000` (seconds) or higher if:
- Your API quota has been exceeded
- Your account is rate-limited due to excessive requests
- You're making too many concurrent enrichment requests

When `muti-asset_portfolio.csv` is processed:
- Each position (stock or bond) triggers API calls
- Each bond calls `get_bond_prices()`
- Multiple bonds hitting the API quickly = quota exhaustion
- FactSet returns `Retry-After: 36000` (10 hours)
- Client blocks for 10 hours waiting

## The Problem

### Current Behavior
```
Position 1: API call ✓
Position 2: API call ✓
...
Position N: API call → 429 Rate Limited
           → "Please wait 36000 seconds (10 hours)"
           → app.sleep(36000) ← BLOCKS FOR 10 HOURS
           → retry
```

### Why This Is Bad
1. **Blocks the entire enrichment process** - no other positions can be processed
2. **No visibility** - only a warning log, no clear user-facing message
3. **No graceful degradation** - just sleeps instead of handling it
4. **Wasted resources** - app sits idle for 10 hours

## Recommended Solutions

### Option 1: Cap the Retry-After (Quick Fix)
Limit maximum wait time to something reasonable (e.g., 5 minutes):

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 5))
    max_wait = 300  # 5 minutes max
    retry_after = min(retry_after, max_wait)

    if retry_after > max_wait:
        logger.warning(
            f"Rate limited with {retry_after}s retry requested. "
            f"Capping to {max_wait}s to prevent excessive wait."
        )

    logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry...")
    time.sleep(retry_after)
```

### Option 2: Fail Fast (Better UX)
Return an error after first 429 instead of waiting:

```python
if response.status_code == 429:
    raise FactSetClientError(
        "Rate limit exceeded. Your FactSet API quota has been exhausted. "
        "Please try again later or contact FactSet support."
    )
```

### Option 3: Implement Request Queueing (Production-Grade)
- Queue API requests instead of making them synchronously
- Track rate limits per endpoint
- Implement backpressure handling
- Use async processing

## Current Configuration

**Rate Limiting Settings:**
- Requests per second: 10 RPS (line 49 of factset_client.py)
- Request timeout: 30 seconds (line 50)
- Max retries: 3 attempts (line 85)
- Exponential backoff: 2-10 second range (line 86)

These are good, but they don't protect against the 429 Retry-After header blocking.

## Testing the Multi-Asset Portfolio

**Expected behavior with `muti-asset_portfolio.csv`:**
- Row 24 has a Fixed Coupon Bond (CUSIP: 037833BY5)
- Enrichment would call API for this bond
- If API quota is already consumed, returns 429 with long Retry-After
- Client blocks for duration specified in header

## Diagnosis Checklist

To confirm this is what happened:
- ✓ Check Streamlit/app logs for warning: "Rate limited. Waiting..."
- ✓ Check how long it waited before proceeding or failing
- ✓ Check if it's stuck at specific position enrichment

## Next Steps

1. **Immediate**: Check the logs from your debug_multi_etl.py run to see if rate limiting message appeared
2. **Short-term**: Implement Option 1 (cap retry-after) as a safety measure
3. **Long-term**: Consider Option 3 (queue-based processing) for production use

---

**Note**: This is NOT a bug in your ETL logic. It's a rate-limiting interaction with FactSet's API that needs better UX handling.
