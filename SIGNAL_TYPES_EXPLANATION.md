# Explanation of Unassigned Signals

## Overview
Some signals appear in the "Unassigned" sheet because they cannot be assigned to available IO modules. This document explains why.

## Signal Types in Unassigned Sheet

### 1. SOFT Signals (Software/Alarm Signals)
**Status:** In Unassigned sheet ✓ **CORRECT**

**Reason:** 
- SOFT signals are software-based alerts, alarms, and status indicators
- They do NOT require physical IO hardware
- The FIO (Field Input/Output) module catalog contains only physical hardware modules:
  - SAI143-S (Analog Input, 16 channels)
  - SAI143-H (Analog Input with HART, 16 channels)
  - SDV144-S (Digital Input, 16 channels)
  - SDV541-S (Digital Output, 8 channels)

**Expected Behavior:**
- SOFT signals should NOT be assigned to any FIO module
- These are handled separately in the system as software/alarm logic
- Having SOFT signals in the Unassigned sheet is the CORRECT behavior

---

### 2. DI-RL with Redundancy (DI-RL marked with Y)
**Status:** Some in Assigned, Some in Unassigned (Capacity Limited)

**Reason:**
- DI-RL signals with redundancy flag 'Y' require **2 consecutive physical slots**
  - Slot 1 (odd slot): Signal assigned here
  - Slot 2 (even slot): Reserved for redundancy
  - Next available slot: Slot 3 (odd slot for next redundant pair)
  
- Available capacity for redundant DI signals:
  - SDV144-S module: 16 channels per instance
  - With redundancy: Only 8 channel pairs available (odd slots 1, 3, 5, 7, etc.)
  - Limited by number of available nodes and slots

**Example:**
```
If you have 100 DI-RL redundant signals but only 8 physical slot-pairs available:
- First 8 redundant signals → ASSIGNED to slots 1, 3, 5, 7, 9, 11, 13, 15
- Remaining 92 redundant signals → UNASSIGNED (no more slot-pairs available)
```

**Module Capacity Reference:**
| Item | Value |
|------|-------|
| Node-1 slots available | 6 (slots 1-6) |
| Node-2+ slots available | 8 (slots 1-8) |
| DI slots for redundancy per node | Odd slots only (1, 3, 5, 7, etc.) |
| Max redundant DI pairs per node | 3 (Node-1) or 4 (Node-2+) |

---

### 3. DO-R (Digital Output with Redundancy)
**Status:** Some in Assigned, Some in Unassigned (Capacity Limited)

**Reason:**
- Same as DI-RL: Redundancy requires 2 consecutive slots
- SDV541-S module: 8 channels per instance
- Limited by available slot-pairs

---

### 4. DO and DI-RL (Non-Redundant)
**Status:** Should be mostly assigned if modules exist

If these appear in Unassigned:
- **Check:** Are the required modules (SDV541-S for DO, SDV144-S for DI) present in the hardware catalog?
- **Reason:** If modules don't exist → signals cannot be assigned
- **Solution:** Add missing modules to IO_Module_Catalog sheet in Excel input

---

## Action Items

### For SOFT Signals:
✓ **No action needed** - These should remain unassigned (they're software logic, not hardware)

### For DI-RL(Y) and DO-R(Y):
1. **Check capacity:** Count total redundant signals needed
2. **Plan slots:** Ensure enough nodes/slots exist
3. **If exceeded:** Either:
   - Add more IO modules (increase nodes)
   - Reduce redundancy requirement for some signals
   - Add external IO cards

### For DO and DI-RL (non-redundant):
1. Verify IO modules are listed in IO_Module_Catalog
2. Check module counts are sufficient
3. Review any error messages in the output

---

## Summary

| Signal Type | Expected Location | Reason |
|------------|------------------|--------|
| SOFT | Unassigned | Software signals, no hardware module |
| DI-RL (Y) | Assigned or Unassigned | Assigned if capacity; Unassigned if full |
| DO-R (Y) | Assigned or Unassigned | Assigned if capacity; Unassigned if full |
| DI-RL (N) | Assigned | Should be assigned if module exists |
| DO (N) | Assigned | Should be assigned if module exists |

---

## Excel Output Format (Applied)

✓ **Formatting completed:**
- Column widths: Auto-fitted to content in all 3 sheets (Assigned, Unassigned, Summary)
- Freeze panes: First row (headers) frozen in Assigned and Unassigned sheets
- Sorting: Data sorted by Slot (ascending), then Node (ascending)
