# Comprehensive Refactoring Plan - Unified Signal + Spare Assignment

## Executive Summary
This refactoring consolidates the currently fragmented signal and wired spare assignment logic into a single, unified flow where:
1. Wired spares are **pre-calculated** before module assignment
2. Synthetic wired spare rows are **injected into df_instruments** before assignment
3. Module count calculation **includes spares from the start**
4. A single assignment loop handles **both signals and spares together**
5. Empty channel slots are **tracked and distributed equally** across modules

---

## Current Problem

### Current Flow (Fragmented)
```
assign_modules()
  ├─ Read df_instruments (contains only SIGNALS)
  ├─ Call assign_modules_intelligent()
  │  └─ Assigns only signals to modules 1-16 per type
  ├─ Call generate_wired_spares()
  │  └─ Creates spare tags AFTER signals assigned
  └─ Spares added to empty channels (no equal distribution)
```

### Issues
1. **No pre-planning**: Module count calculated without considering spares
2. **Two-stage assignment**: Signals first, spares second (uncoordinated)
3. **Unequal distribution**: Spares added ad-hoc to first available slots
4. **No tracking**: Empty channel slots not tracked or managed
5. **Maintenance nightmare**: Logic split across multiple functions

---

## Refactoring Solution

### New Unified Flow
```
assign_modules()
  ├─ Read df_instruments (SIGNALS ONLY)
  ├─ [NEW] Pre-calculate wired spares per IO type
  ├─ [NEW] Create synthetic wired spare rows with flag is_wired_spare=True
  ├─ [NEW] Inject synthetic rows into df_instruments
  ├─ [NEW] Recalculate module count (signals + spares)
  ├─ [NEW] Calculate empty slots per module
  ├─ Call assign_modules_intelligent() [MODIFIED]
  │  └─ Unified loop: assign signals + spares + empty slots together
  │     - Track which channels are empty
  │     - Distribute empty slots equally
  │     - Mark wired spares with appropriate tags
  └─ Return unified results
```

---

## Implementation Details

### Step 1: Pre-Calculate Wired Spares Count
**Location**: `ChannelAssignmentManager.assign_modules()` → NEW method

**New Method**: `calculate_wired_spares_needed()`
```python
def calculate_wired_spares_needed(self, df_instruments):
    """
    Pre-calculate wired spares count per IO type BEFORE assignment
    
    Returns:
        dict: {
            'DI': {
                'total_signals': int,
                'wired_spares_needed': int,
                'total_items': int,
                'modules_required': int,
                'empty_channels_per_module': int,
                'empty_channels_distribution': dict
            },
            'DO': {...},
            'AI': {...},
            'AO': {...}
        }
    """
    wired_spare_config = self.read_wired_spares_config()
    
    # Count signals per type
    signal_counts = df_instruments['IO_TYPE'].value_counts().to_dict()
    
    # Calculate spares needed per type
    results = {}
    for io_type in ['DI', 'DO', 'AI', 'AO']:
        signal_count = signal_counts.get(io_type, 0)
        spare_factor = wired_spare_config.get(io_type, {}).get('spare_factor', 0)
        
        wired_spares = math.ceil(signal_count * spare_factor)
        total_items = signal_count + wired_spares
        modules_needed = math.ceil(total_items / 16)
        empty_channels = (modules_needed * 16) - total_items
        
        # Calculate equal distribution of empty channels
        empty_per_module = empty_channels // modules_needed
        empty_remainder = empty_channels % modules_needed
        
        results[io_type] = {
            'total_signals': signal_count,
            'wired_spares_needed': wired_spares,
            'total_items': total_items,
            'modules_required': modules_needed,
            'total_empty_channels': empty_channels,
            'empty_channels_per_module': empty_per_module,
            'modules_with_extra_empty': empty_remainder
        }
    
    return results
```

### Step 2: Create and Inject Synthetic Wired Spare Rows
**Location**: `ChannelAssignmentManager.assign_modules()` → NEW code block

```python
# Step 2: Create synthetic wired spare rows
spare_calculations = self.calculate_wired_spares_needed(df_instruments)

synthetic_spares_list = []
spare_tag_counter = {}

for io_type, calc in spare_calculations.items():
    spare_count = calc['wired_spares_needed']
    spare_tag_counter[io_type] = 0
    
    for i in range(spare_count):
        spare_tag = f"WIRED_SPARE_{io_type}_{spare_tag_counter[io_type]:03d}"
        spare_tag_counter[io_type] += 1
        
        synthetic_spares_list.append({
            'PID_TAG': spare_tag,
            'IO_TYPE': io_type,
            'SIGNAL_TYPE': 'Spare',  # Mark as spare
            'MODULE_NUMBER': None,   # Will be assigned
            'CHANNEL_NUMBER': None,  # Will be assigned
            'is_wired_spare': True,  # Synthetic flag
            # ... other required columns as None or defaults
        })

df_synthetic_spares = pd.DataFrame(synthetic_spares_list)

# Inject into df_instruments BEFORE assignment
df_instruments = pd.concat([df_instruments, df_synthetic_spares], ignore_index=True)
```

### Step 3: Modify assign_modules_intelligent() - Unified Assignment Loop

**Key Changes**:
1. Accept `wired_spare_calculations` as parameter
2. Track empty channel slots per module
3. Unified loop for signals + spares + empty slots
4. Equal distribution of empty slots

```python
def assign_modules_intelligent(self, wired_spare_calculations=None):
    """
    Unified assignment of signals + spares + empty slots
    
    Each IO type follows pattern:
    - Channels 1-16 per module
    - Assign signals first
    - Distribute spares evenly
    - Distribute empty slots evenly
    """
    
    for io_type in ['DI', 'DO', 'AI', 'AO']:
        # Get items to assign (both signals and synthetic spares)
        items = df_instruments[
            df_instruments['IO_TYPE'] == io_type
        ].reset_index(drop=True)
        
        if len(items) == 0:
            continue
        
        calc = wired_spare_calculations[io_type]
        modules_count = calc['modules_required']
        empty_slots_per_module = calc['empty_channels_per_module']
        modules_with_extra_empty = calc['modules_with_extra_empty']
        
        # Separate signals and spares
        signals = items[items.get('is_wired_spare', False) == False]
        spares = items[items.get('is_wired_spare', False) == True]
        
        # Assignment loop
        module_channel_map = {m: [] for m in range(1, modules_count + 1)}
        channel_number = 1
        current_module = 1
        
        # Phase 1: Assign signals
        for idx, signal in signals.iterrows():
            df_instruments.loc[signal.name, 'MODULE_NUMBER'] = current_module
            df_instruments.loc[signal.name, 'CHANNEL_NUMBER'] = channel_number
            module_channel_map[current_module].append(channel_number)
            
            channel_number += 1
            if channel_number > 16:
                current_module += 1
                channel_number = 1
        
        # Phase 2: Assign spares
        for idx, spare in spares.iterrows():
            df_instruments.loc[spare.name, 'MODULE_NUMBER'] = current_module
            df_instruments.loc[spare.name, 'CHANNEL_NUMBER'] = channel_number
            module_channel_map[current_module].append(channel_number)
            
            channel_number += 1
            if channel_number > 16:
                current_module += 1
                channel_number = 1
        
        # Phase 3: Track empty channels
        empty_slots = {}
        for mod in range(1, modules_count + 1):
            used_channels = len(module_channel_map[mod])
            empty_count = 16 - used_channels
            
            # Add extra empty slot to first N modules if needed
            if mod <= modules_with_extra_empty:
                empty_count += 1
            
            empty_slots[mod] = [
                ch for ch in range(1, 17) 
                if ch not in module_channel_map[mod]
            ][:empty_count]
```

### Step 4: Update Main assign_modules() Method

```python
def assign_modules(self):
    """Main orchestration method"""
    
    # Read instruments
    df_instruments = self.read_instrument_file()
    
    # [NEW] Pre-calculate wired spares
    wired_spare_calculations = self.calculate_wired_spares_needed(df_instruments)
    
    # [NEW] Create and inject synthetic spare rows
    df_instruments = self.inject_synthetic_wired_spares(
        df_instruments, 
        wired_spare_calculations
    )
    
    # [MODIFIED] Call unified assignment
    success = self.assign_modules_intelligent(wired_spare_calculations)
    
    # [REMOVED] No more separate generate_wired_spares() call needed
    # Spares are already assigned during unified loop
    
    return success
```

---

## Data Flow Diagram

### Before (Current)
```
df_instruments (SIGNALS ONLY)
           ↓
assign_modules_intelligent()  [Channels 1-16 per module]
           ↓
df_modules (SIGNALS ASSIGNED)
           ↓
generate_wired_spares()       [Creates SPARE tags]
           ↓
df_results (SIGNALS + SPARES) [UNEQUAL DISTRIBUTION]
```

### After (Refactored)
```
df_instruments (SIGNALS ONLY)
           ↓
calculate_wired_spares_needed() [PRE-CALCULATES spare count]
           ↓
inject_synthetic_wired_spares() [ADDS SYNTHETIC ROWS]
           ↓
df_instruments (SIGNALS + SYNTHETIC SPARES)
           ↓
assign_modules_intelligent()  [UNIFIED LOOP]
  ├─ Phase 1: Assign signals (Ch 1-16)
  ├─ Phase 2: Assign spares (Ch 1-16 sequentially)
  ├─ Phase 3: Track empty channels
  └─ Phase 4: Distribute empty slots equally
           ↓
df_results (SIGNALS + SPARES) [EQUAL DISTRIBUTION]
```

---

## Key Benefits

1. **Pre-Planning**: Module count calculated with full knowledge of signal + spare count
2. **Unified Logic**: Single assignment loop, no fragmentation
3. **Equal Distribution**: 
   - Empty slots distributed evenly across modules
   - Remainder slots distributed to first N modules
4. **Maintainability**: All logic in one place, easy to understand and modify
5. **Correctness**: Guarantees no overlapping channel assignments
6. **Traceability**: Each spare marked with `is_wired_spare=True` and `WIRED_SPARE_*` tag

---

## Implementation Checklist

- [ ] Create `calculate_wired_spares_needed()` method
- [ ] Create `inject_synthetic_wired_spares()` method  
- [ ] Modify `assign_modules_intelligent()` for unified loop
- [ ] Update `assign_modules()` orchestration
- [ ] Remove/deprecate `generate_wired_spares()` method
- [ ] Test with sample data (DI, DO, AI, AO)
- [ ] Verify equal distribution of empty channels
- [ ] Verify no overlapping channel assignments
- [ ] Update documentation

---

## Testing Strategy

### Test Case 1: Single IO Type
- Input: 20 DI signals, 20% spare factor → 4 spares needed
- Expected: 2 modules, 24 items total, 8 empty slots
- Verify: 4 empty slots per module

### Test Case 2: Multiple IO Types
- Input: DI=30, DO=20, AI=15, AO=10
- Calculate spares for each
- Verify: Correct module count per type

### Test Case 3: Edge Case (Perfect Division)
- Input: 16 DI signals, 0 spares
- Expected: 1 module, 16 channels, 0 empty
- Verify: No empty channels

### Test Case 4: Remainder Distribution
- Input: 33 DI signals (with spares) → 3 modules needed, 15 empty total
- Expected: 5 empty per module, 0 remainder
- Verify: Equal distribution

---

## Files to Modify

1. **processors/channel_assignment_manager.py**
   - Add `calculate_wired_spares_needed()`
   - Add `inject_synthetic_wired_spares()`
   - Modify `assign_modules_intelligent()`
   - Update `assign_modules()`

2. **Design Input Review.py**
   - Update pipeline if needed

3. **test_*.py files**
   - Add comprehensive tests for unified logic

---

## Rollback Plan

Keep current `generate_wired_spares()` method commented out for 1-2 versions before removal. This allows easy rollback if issues arise.

---

## Notes

- Synthetic wired spare rows should have `is_wired_spare=True` to distinguish from signal rows
- Each spare tagged as `WIRED_SPARE_{IO_TYPE}_{counter:03d}` for traceability
- Empty channel slots are calculated but NOT assigned to specific instruments (they remain unassigned in df_results)
- All spares MUST be assigned before empty slots are distributed
