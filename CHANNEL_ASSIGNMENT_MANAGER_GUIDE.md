# Intelligent Channel Assignment Manager - Implementation Guide

## Overview

A new, intelligent channel assignment system has been implemented to replace the old module-by-module assignment logic. This system is cleaner, more maintainable, and provides better control over signal-to-module allocation.

## Architecture

### Class: `ChannelAssignmentManager`
**Location:** `processors/channel_assignment_manager.py`

A dedicated class that handles all aspects of intelligent channel assignment. This keeps the business logic separate and makes the code more readable.

## Key Features

### 1. **Module-by-Module Processing**
- Processes one module at a time (Node-1/Slot-1 first, then Slot-2, etc.)
- Groups signals by module type (AI, DI, DO, etc.)
- Fills all signals of the same type into one module before moving to the next
- Ensures organized, sequential assignment

### 2. **Wired Spare Distribution**
- Automatically calculates total wired spares from input data
- Distributes wired spares **evenly** across all modules
- If 20 wired spares and 10 AI modules: adds 2 wired spares to each module
- Ensures balanced load distribution

### 3. **Empty Channel Management**
- Ensures each module has at least 1 empty channel when possible
- Distributes empty channels evenly if not all modules can have 1 empty
- Optimal hardware utilization without overloading

### 4. **Data Analysis Phase**
Before any assignment happens:
- Counts total signals and wired spares
- Groups signals by IO type (AI, DI, DO, AO)
- Determines module specifications from hardware config
- Calculates module count needed
- Creates an allocation plan

## Usage

### Method: `assign_modules_intelligent()`
**Location:** `Design Input Review.py` (new method)

Called from the main flow instead of the old `assign_modules()` method.

```python
reviewer = DesignInputReview(...)
reviewer.extract_required_columns()
reviewer.apply_user_inputs()
reviewer.sort_by_pid_tag()
reviewer.read_hardware_config()
reviewer.read_mounting_rule()
reviewer.read_controller_limits()

# NEW: Use intelligent assignment instead of old assign_modules()
if reviewer.assign_modules_intelligent():
    print("✓ Intelligent assignment successful")
else:
    print("✗ Assignment failed")

# Continue with rest of flow...
reviewer.assign_nodes_and_controllers()
reviewer.generate_output_file()
```

## API Overview

### ChannelAssignmentManager Methods

#### `__init__(df_instruments, df_hardware)`
Initializes the manager with signal and hardware data.

```python
manager = ChannelAssignmentManager(
    df_instruments=df_points,  # DataFrame with signals
    df_hardware=df_hardware_config  # DataFrame with module specs
)
```

#### `analyze_and_plan() -> Dict`
Analyzes input data and creates an allocation plan. Must be called before `assign_channels()`.

**Returns:**
```python
{
    'success': bool,                      # True if analysis succeeded
    'total_signals': int,                 # Count of actual signals
    'total_wired_spares': int,           # Count of wired spares
    'total_modules': int,                # Modules needed
    'channels_per_module': int,          # Capacity of each module
    'wired_spares_per_module': float,    # Average spares per module
    'signal_groups': Dict[str, int],     # {IO_Type: count}
    'module_plan': List[Dict]            # Detailed allocation plan
}
```

**Example:**
```python
analysis = manager.analyze_and_plan()
if analysis['success']:
    print(f"Need {analysis['total_modules']} modules")
    print(f"Each module gets {analysis['wired_spares_per_module']:.1f} wired spares")
```

#### `assign_channels(node_start=1, slot_start=1) -> pd.DataFrame`
Executes the allocation plan and assigns channels to all signals.

**Parameters:**
- `node_start`: Starting node number (default: 1)
- `slot_start`: Starting slot number (default: 1)

**Returns:** DataFrame with assignments (Module_Name, Node, Slot, Channel, etc.)

**Example:**
```python
df_assigned = manager.assign_channels(node_start=1, slot_start=1)
print(f"Assigned {len(df_assigned[df_assigned['Channel'] > 0])} items")
```

#### `get_summary_report() -> str`
Generates a human-readable summary of the allocation plan.

**Example:**
```python
print(manager.get_summary_report())
# Output:
# ====================================
# CHANNEL ASSIGNMENT PLAN SUMMARY
# ====================================
# Total Modules: 3
# Wired Spares per Module: 2.50
# 
# MODULE ALLOCATION DETAILS:
# Module 1:
#   Location: Node 1, Slot 1
#   Type: AI
#   Capacity: 16 channels
#   ...
```

## Comparison: Old vs New

### Old Method (assign_modules)
- Complex nested loops with many conditions
- Mixed business logic in DesignInputReview class
- Hard to understand assignment flow
- Difficult to debug and maintain
- No clear separation of concerns

### New Method (assign_modules_intelligent)
- Clean separation: manager handles assignment logic
- Clear phases: Analyze → Plan → Assign
- Easy to test each phase independently
- Readable, maintainable code structure
- Clear logging and reporting

## Implementation Details

### Data Flow

```
Input Data (df_instruments, df_hardware)
    ↓
[Phase 1] ANALYZE
    - Count signals by type
    - Count wired spares
    - Group signals by IO_type
    ↓
[Phase 2] PLAN
    - Determine modules needed
    - Create allocation plan
    - Calculate spare distribution
    ↓
[Phase 3] ASSIGN
    - Assign actual channels
    - Distribute wired spares
    - Create assignment DataFrame
    ↓
Output: df_assigned with Node, Slot, Channel for each signal
```

### Wired Spare Distribution Example

**Input:**
- 20 wired spares total
- 10 AI modules needed (each with 16 channels)

**Calculation:**
- Spares per module = 20 / 10 = 2.0
- Each module gets exactly 2 wired spares

**Assignment:**
```
Module 1: 14 signals + 2 wired spares = 16 channels (0 empty)
Module 2: 14 signals + 2 wired spares = 16 channels (0 empty)
Module 3: 14 signals + 2 wired spares = 16 channels (0 empty)
...
Module 10: 14 signals + 2 wired spares = 16 channels (0 empty)
```

### Empty Channel Distribution Example

**Input:**
- 50 signals total
- 8 modules needed (each with 16 channels)

**Calculation:**
- Signals per module = 50 / 8 = 6.25 → 6 signals per module
- Remaining: 50 - (6 × 8) = 2 signals
- So: 6 modules with 6 signals + 2 modules with 7 signals
- Empty channels: 10 in 6 modules, 9 in 2 modules

**Distribution:** Roughly equal across all modules

## Files Modified

### New Files
1. **processors/channel_assignment_manager.py** - The new intelligent manager class

### Modified Files
1. **Design Input Review.py**
   - Added import for ChannelAssignmentManager
   - Added new method `assign_modules_intelligent()`

## Migration Guide

### To Switch to New Method

In `Design Input Review.py` main flow, replace:
```python
# OLD:
if not reviewer.assign_modules():
    raise Exception("Failed to assign modules")
```

With:
```python
# NEW:
if not reviewer.assign_modules_intelligent():
    raise Exception("Failed to assign modules intelligently")
```

### Backward Compatibility
The old `assign_modules()` method remains untouched, so existing code continues to work. Both methods can coexist during transition period.

## Logging

The manager provides detailed logging at each step:

```
[ChannelAssignmentManager] Initialized with 250 signals and 5 hardware configs
[ChannelAssignmentManager] Starting analysis and planning...
  - Total items: 250
  - Actual signals: 240
  - Wired spares: 10
  - Signal groups: {'AI': 120, 'DI': 80, 'DO': 40}
  - Modules needed: 4
  - Channels per module: 16
[ChannelAssignmentManager] Created allocation plan with 4 modules
[ChannelAssignmentManager] Assigning channels starting from Node 1, Slot 1...
  - Processing 240 signals and 10 wired spares
  - Processing 240 signals...
[ChannelAssignmentManager] Channel assignment complete. 250 assignments made
```

## Testing

To test the new manager independently:

```python
import pandas as pd
from processors.channel_assignment_manager import ChannelAssignmentManager

# Load your data
df_signals = pd.read_excel("your_signals.xlsx")
df_hardware = pd.read_excel("your_hardware.xlsx")

# Create and test manager
manager = ChannelAssignmentManager(df_signals, df_hardware)
analysis = manager.analyze_and_plan()
print(analysis)

df_assigned = manager.assign_channels()
print(df_assigned[['PID_TAG', 'Module_Name', 'Node', 'Slot', 'Channel']].head(10))
```

## Future Enhancements

Potential improvements to the manager:

1. **Redundancy Flag Integration**: Skip even slots when `Redundancy_Flag=Yes`
2. **IS/NIS Separation**: Separate IS and NIS signals to different module instances
3. **Temperature-Based Capacity**: Adjust channel capacity based on operating temperature
4. **HART Module Support**: Prioritize HART-capable modules for HART signals
5. **Custom Channel Ordering**: Support different channel assignment strategies (odd-first for redundant, sequential for non-redundant, etc.)

## Troubleshooting

### Issue: "No allocation plan created yet"
**Cause:** `assign_channels()` called before `analyze_and_plan()`
**Fix:** Always call `analyze_and_plan()` first

### Issue: Fewer modules than expected
**Cause:** Higher module capacity or fewer signals than calculated
**Fix:** Check signal count and module specs in `analyze()` output

### Issue: Uneven wired spare distribution
**Cause:** Wired spare count not divisible by module count
**Fix:** Normal behavior - some modules get +1 spare. This is intentional.

## Summary

The ChannelAssignmentManager provides a cleaner, more maintainable approach to channel assignment. By separating the assignment logic into a dedicated class, the code is more testable, readable, and easier to enhance in the future.

**Key Benefits:**
✅ Clean separation of concerns
✅ Module-by-module processing
✅ Even wired spare distribution
✅ Detailed logging and reporting
✅ Easy to test and debug
✅ Maintainable code structure
