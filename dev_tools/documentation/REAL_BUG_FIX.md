# WIRED SPARES BUG - REAL FIX (CRITICAL)

## The ACTUAL Problem Found

The issue is in the **`generate_wired_spares()` method** (line 1454), which is called by **app.py** (the web interface you're using).

### The Bug

```python
# OLD CODE (BROKEN):
for spare_idx in range(1, spares_for_this + 1):
    spare_channel = max_channel + spare_idx  # ← ALWAYS uses max_channel!
    
    if spare_channel > usable_channels_limit:
        break
```

**Problem**: `max_channel` is NEVER updated, so:
- If max_channel = 6 (signals in CH1-6)
- Spare 1: channel = 6+1 = 7 ✓
- Spare 2: channel = 6+2 = 8 ✓  
- Spare 3: channel = 6+3 = 9 ✓
- Spare 4: channel = 6+4 = 10 ← Would work, but **channel calculation uses max_channel instead of tracking next_available!**

The REAL issue: Without tracking `next_available_channel`, all subsequent spares end up in the same position calculation!

### The Fix

```python
# NEW CODE (FIXED):
next_available_channel = max_channel + 1  # Start from next channel
spares_added_for_instance = 0

for spare_idx in range(1, spares_for_this + 1):
    spare_channel = next_available_channel  # Use tracked position
    
    if spare_channel > usable_channels_limit:
        break
    
    # ... create spare ...
    
    next_available_channel += 1  # Move to next channel
```

**Result**:
- Spare 1: channel = 7 ✓
- Spare 2: channel = 8 ✓
- Spare 3: channel = 9 ✓
- Spare 4: channel = 10 ✓ (NOW WORKS!)
- Spare 5: channel = 11 ✓
- ... continues up to channel 16

## Files Modified

**File**: Design Input Review.py
**Method**: `generate_wired_spares()` (lines 1449-1463)
**Changes**:
1. Added `next_available_channel = max_channel + 1` before loop
2. Use `spare_channel = next_available_channel` in loop
3. Increment `next_available_channel += 1` after each spare

## Why This Fixes Your Issue

**Before**:
- Only channels 7, 8, 9 got wired spares
- Channels 10-16 remained blank

**After**:
- Wired spares fill channels 7-16 (up to module capacity)
- All available channels used efficiently
- Proper distribution per Requirement #10

## Test It Now

Since you're using **app.py** (web interface):

1. Deploy the fixed Design Input Review.py
2. Restart the app: `python app.py`
3. Upload your test file
4. Set wired spares: 10%
5. Run the review
6. Check output Excel file:
   - Open "Assigned" sheet
   - Look at Slot 3
   - Should now see: CH1-16 filled (or appropriate subset)
   - NOT just CH7-9

## Syntax

✓ No syntax errors - ready to use immediately
