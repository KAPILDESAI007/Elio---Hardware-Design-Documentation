# Channel-Based Redundancy Logic - Implementation Summary

## Changes Made

### 1. **Redundancy Understanding - CORRECTED**

**OLD (Incorrect):**
- Thought redundancy meant 2 consecutive SLOTS (Slot 1-2, 3-4, 5-6...)
- Limited capacity significantly

**NEW (Correct):**
- Redundancy is CHANNEL-based, not SLOT-based
- Slots fill sequentially (1, 2, 3, 4, 5, 6...)
- Within each slot, redundant signals use ODD CHANNELS ONLY (1, 3, 5, 7, 9, 11, 13, 15)
- Even channels (2, 4, 6, 8, 10, 12, 14, 16) are reserved for redundancy

### 2. **Code Changes in Design Input Review.py**

#### A. assign_modules() Method - Docstring Updated (Line 344-350)
```python
"""
Assign instruments to modules with comprehensive constraints:
1. Redundancy: For redundant signals, use odd channels (1,3,5,7...) and leave even channels empty (2,4,6,8...)
2. IS/NIS: All {IO_Type}-IS in one module, all {IO_Type}-NIS in separate module
3. HART: Filter based on Supports_HART
4. Temperature: Adjust capacity based on ambient_Max_C and temperature_rating
5. Slots fill sequentially, regardless of redundancy
"""
```

#### B. Module Instance Tracking - Changed (Line 453-456)
**OLD:**
```python
'channels_used': 0,
'is_redundant': False,
```

**NEW:**
```python
'channels_per_slot': [0] * 8,  # Track channels used per slot (0-7 for max 8 slots)
```
Now tracks how many channels are used in EACH slot (not just total)

#### C. Channel Allocation Logic - REWRITTEN (Line 467-520)

**NEW LOGIC:**

For **REDUNDANT signals**:
- Use ODD CHANNELS ONLY: 1, 3, 5, 7, 9, 11, 13, 15
- Each signal takes 1 odd channel
- The next even channel remains empty
- Within each slot:
  - channels_per_slot[0] = 0 → next odd channel is 1
  - channels_per_slot[0] = 1 → next odd channel is 3
  - channels_per_slot[0] = 2 → next odd channel is 5
  - And so on...

```python
odd_channels = [1, 3, 5, 7, 9, 11, 13, 15]
next_odd_idx = channels_used  # Index into the odd_channels list
if next_odd_idx < len(odd_channels):
    next_channel = odd_channels[next_odd_idx]
```

For **NON-REDUNDANT signals**:
- Use ANY AVAILABLE CHANNEL sequentially: 1, 2, 3, 4, 5...
- Each signal takes 1 channel
- No channels are reserved

### 3. **Sorting - UPDATED (Line 1289-1296)**

**OLD:**
```python
Sort assigned data by Slot first, then by Node
sort_values(by=['Slot_Sort', 'Node_Sort'])
```

**NEW:**
```python
Sort assigned data by Node, then Slot, then Channel
sort_values(by=['Node_Sort', 'Slot_Sort', 'Channel_Sort'])
```

## Example Output Pattern

### For AI-R Redundant Signals (IO_REDUNDANCY='Y'):
```
PID_TAG              Node  Slot  Channel  Redundancy_Flag
0122-EAI-040109        1     1        1     Yes
494-PIT-128B/06        1     1        3     Yes
0122-EAI-050109        1     1        5     Yes
0122-EAI-080115        1     2        1     Yes
0123-EAI-020111        1     2        3     Yes
```

**Pattern:** 
- Slots fill sequentially (1, 1, 1... then 2, 2, 2...)
- Channels are odd: 1, 3, 5, 7, 9, 11, 13, 15 within each slot
- Even channels (2, 4, 6, 8...) are left empty for redundancy

### Sorting Order:
- Node 1, Slot 1 (all signals)
- Node 1, Slot 2 (all signals)
- Node 1, Slot 3 (all signals)
- ... more slots in Node 1
- Node 2, Slot 1 (all signals)
- Node 2, Slot 2 (all signals)
- ... and so on

## Capacity Impact

### OLD (Slot-based, WRONG):
- 224 DI-RL signals with 2 slots per redundant signal
- Need: 224 × 2 = 448 slots
- Available: ~16 slots total → Only 53 could fit (WRONG)

### NEW (Channel-based, CORRECT):
- 224 DI-RL signals using odd channels only
- Per slot: 8 odd channels available (1, 3, 5, 7, 9, 11, 13, 15)
- Per 8-slot module instance: 8 × 8 = 64 signals possible
- Per node: Multiple module instances → Much higher capacity
- ALL 224 can now be assigned (if enough nodes exist)

## Verification

When you run the tool:
1. ✅ All AI-R signals will have `Redundancy_Flag = 'Yes'`
2. ✅ Channels for redundant signals will be: 1, 3, 5, 7, 9, 11, 13, 15 in each slot
3. ✅ Data will be sorted: Node (ascending) → Slot (ascending) → Channel (ascending)
4. ✅ DI-RL signals can now use both odd and even channels (non-redundant) OR odd only (redundant)
5. ✅ Much higher capacity for redundant signals

## Testing the Changes

Run with your input data:
1. Upload Excel files through the web app
2. Download output file
3. Check:
   - Assigned sheet has signals sorted by Node, Slot, Channel
   - Redundant signals (IO_REDUNDANCY='Y') use channels 1, 3, 5, 7, 9, 11, 13, 15
   - Much fewer signals in Unassigned sheet
   - 494-HS-459A should now be ASSIGNED (if there's capacity)

## Summary

✅ **Redundancy is now correctly understood as CHANNEL-wise**
✅ **Slots fill sequentially regardless of redundancy**
✅ **Redundant signals get odd channels, even channels reserved**
✅ **Much higher capacity achieved**
✅ **Sorting is Node → Slot → Channel**
