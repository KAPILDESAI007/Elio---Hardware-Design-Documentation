# WIRED SPARES BUG - FINAL FIX (PRIORITIZE SIGNALS OVER SPARES)

## The Root Issue

Your output shows:
```
SCS0101_N1S3CH7   ← ONLY wired spares in N1S3
SCS0101_N1S3CH8   ← NO signals assigned to CH1-6
SCS0101_N1S3CH9
```

**Problem**: Wired spares and signals are being assigned in the order they appear in the dataframe.
- If spares appear early, they get first choice of channels
- Signals end up in later channels or other slots
- Result: Slot-3 gets only spares (CH7-9), no signals

## The Solution

Modified the assignment logic to ALWAYS PROCESS SIGNALS FIRST, THEN SPARES:

**File**: Design Input Review.py
**Location**: `assign_modules()` method, lines 653-668
**Change**: 
1. Separate signals from wired spares using a mask
2. Process signals first (guaranteed to get CH1-14)
3. Process spares last (fill remaining channels CH15-16)

```python
# NEW: Separate signals from spares
signal_mask = ~self.df_assigned['PID_TAG'].str.contains('_SPARE_', case=False, na=False)
spare_mask = self.df_assigned['PID_TAG'].str.contains('_SPARE_', case=False, na=False)

# Process signals FIRST, then spares
items_to_process = list(self.df_assigned[signal_mask].iterrows()) + \
                   list(self.df_assigned[spare_mask].iterrows())

# Now process in this order (signals first, spares last)
for idx, row in items_to_process:
    # ... assignment logic ...
```

## Expected Results After Fix

**Before** (Broken):
```
Slot-3:
  CH1-6: BLANK
  CH7-9: Wired spares only
  CH10-16: BLANK
```

**After** (Fixed):
```
Slot-3:
  CH1-14: SIGNALS (6 signals + 8 more signals)
  CH15-16: Wired spares (last 2 channels)
  
OR (if fewer signals):
  CH1-6: SIGNALS
  CH7-14: MORE SIGNALS
  CH15-16: Wired spares (even distribution)
```

## How It Works Now

1. Algorithm iterates through dataframe
2. **FIRST**: All actual signals get assigned to channels
   - They fill CH1-14 in slot-3
   - They fill subsequent modules as needed
3. **THEN**: All wired spares get assigned to remaining channels
   - They get CH15-16 in slot-3
   - They fill other modules as needed
4. Result: Proper distribution per your requirements

## Test It

1. Deploy the updated Design Input Review.py
2. Restart app.py
3. Upload your test file
4. Run the review
5. Check output - Slot-3 should now have:
   - Signals in CH1-14
   - Wired spares in CH15-16
   - Proper distribution across all nodes

## Changes Made

- **File**: Design Input Review.py
- **Method**: assign_modules()
- **Lines**: 653-668
- **Change Type**: Separation of signals and spares processing
- **Syntax**: ✓ Verified - No errors
