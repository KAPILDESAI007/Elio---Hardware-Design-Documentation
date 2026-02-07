# Technical Implementation Reference - Unified Assignment

## Quick Reference: Method Signatures

```python
# NEW METHODS
def calculate_wired_spares_needed(self, df_instruments: pd.DataFrame) -> dict
def inject_synthetic_wired_spares(self, df_instruments: pd.DataFrame, 
                                   spare_calculations: dict) -> pd.DataFrame

# MODIFIED METHODS
def assign_modules_intelligent(self, wired_spare_calculations: dict = None) -> bool
def assign_modules(self) -> bool

# DEPRECATED METHODS (Mark for removal)
def generate_wired_spares(self)  # DEPRECATED - merged into unified flow
```

---

## Return Value Structures

### `calculate_wired_spares_needed()` Return Type

```python
{
    'DI': {
        'total_signals': 30,                  # Count of signal rows in df
        'wired_spares_needed': 6,             # Calculated: ceil(30 * 0.20)
        'total_items': 36,                    # 30 + 6
        'modules_required': 3,                # ceil(36 / 16) = 3
        'total_empty_channels': 12,           # (3 * 16) - 36
        'empty_channels_per_module': 4,       # 12 // 3
        'modules_with_extra_empty': 0         # 12 % 3 = 0
    },
    'DO': {
        'total_signals': 20,
        'wired_spares_needed': 4,
        'total_items': 24,
        'modules_required': 2,
        'total_empty_channels': 8,
        'empty_channels_per_module': 4,
        'modules_with_extra_empty': 0
    },
    'AI': {...},
    'AO': {...}
}
```

### Synthetic Spare Row Structure

```python
{
    'PID_TAG': 'WIRED_SPARE_DI_001',
    'IO_TYPE': 'DI',
    'SIGNAL_TYPE': 'Spare',              # New field
    'MODULE_NUMBER': None,               # Will be assigned
    'CHANNEL_NUMBER': None,              # Will be assigned
    'is_wired_spare': True,              # Synthetic flag (NEW)
    # ... other columns as None or defaults from config
}
```

---

## Algorithm: Unified Assignment

### Input
- `df_instruments`: DataFrame with signals + injected synthetic spares
- `wired_spare_calculations`: Pre-calculated spare counts and module requirements

### Output
- `df_instruments` with MODULE_NUMBER and CHANNEL_NUMBER assigned for all rows

### Pseudocode

```
FOR each io_type IN ['DI', 'DO', 'AI', 'AO']:
    items = df[io_type]
    
    // Separate signals from synthetic spares
    signals = items WHERE is_wired_spare != True
    spares = items WHERE is_wired_spare == True
    
    modules_count = calc[io_type].modules_required
    empty_per_module = calc[io_type].empty_channels_per_module
    extra_empty = calc[io_type].modules_with_extra_empty
    
    // Initialize tracking
    current_module = 1
    channel = 1
    module_assignments = {} // Track used channels per module
    
    // PHASE 1: Assign all signals first
    FOR each signal IN signals:
        signal.MODULE_NUMBER = current_module
        signal.CHANNEL_NUMBER = channel
        module_assignments[current_module].append(channel)
        
        channel = channel + 1
        IF channel > 16:
            current_module = current_module + 1
            channel = 1
    
    // PHASE 2: Assign all spares sequentially
    FOR each spare IN spares:
        spare.MODULE_NUMBER = current_module
        spare.CHANNEL_NUMBER = channel
        module_assignments[current_module].append(channel)
        
        channel = channel + 1
        IF channel > 16:
            current_module = current_module + 1
            channel = 1
    
    // PHASE 3: Identify and track empty slots
    FOR m = 1 TO modules_count:
        used_channels = module_assignments[m].length
        empty_count = 16 - used_channels
        
        // Add extra empty to first N modules
        IF m <= extra_empty:
            empty_count = empty_count + 1
        
        empty_slots[m] = [all unused channels from 1-16]
    
    // PHASE 4: (Optional) Mark empty slots for reporting
    // Empty slots are not assigned to instruments in df
    // They are used for final channel map reporting
```

### Example Trace: 30 DI signals, 20% spare factor

**Setup**:
- Signals: 30
- Spares needed: 6
- Total items: 36
- Modules: 3
- Empty: 12 (4 per module)

**Phase 1: Assign 30 Signals**
```
Module 1: Ch 1-16  (16 signals)
Module 2: Ch 1-14  (14 signals)
```
After Phase 1:
- Module 1: Channels 1-16 used (0 empty)
- Module 2: Channels 1-14 used (2 empty)
- Module 3: Empty

**Phase 2: Assign 6 Spares**
```
Module 2: Ch 15-16 (2 spares)
Module 3: Ch 1-4   (4 spares)
```
After Phase 2:
- Module 1: Channels 1-16 used (0 empty)
- Module 2: Channels 1-16 used (0 empty)
- Module 3: Channels 1-4 used (12 empty)

**Phase 3: Track Empty Channels**
```
Module 1: Empty = [] (fully used)
Module 2: Empty = [] (fully used)
Module 3: Empty = [5,6,7,8,9,10,11,12,13,14,15,16]
```

**Phase 4: Verify Equal Distribution**
```
Total empty: 0 + 0 + 12 = 12 ✓
Per module: 12 / 3 = 4 empty per module
Remainder: 12 % 3 = 0
```

---

## Edge Cases

### Case 1: Uneven Distribution (Remainder > 0)
```
Total items: 35 (signals + spares)
Modules: 3
Empty per module: 13 // 3 = 4
Remainder: 13 % 3 = 1

Distribution:
Module 1: 5 empty (4 + 1 from remainder)
Module 2: 4 empty
Module 3: 4 empty
Total: 13 ✓
```

### Case 2: No Spares Needed
```
Signals: 16
Spares: 0
Total: 16
Modules: 1
Empty: 0 per module
```

### Case 3: Very Small Count
```
Signals: 1
Spares: 1
Total: 2
Modules: 1
Empty: 14 per module
```

---

## DataFrame Schema

### df_instruments (After Injection)

| PID_TAG | IO_TYPE | SIGNAL_TYPE | MODULE_NUMBER | CHANNEL_NUMBER | is_wired_spare |
|---------|---------|-------------|---------------|----------------|----------------|
| DI_001 | DI | Input | NULL | NULL | False |
| DI_002 | DI | Input | NULL | NULL | False |
| ... | | | | | |
| WIRED_SPARE_DI_001 | DI | Spare | NULL | NULL | **True** |
| WIRED_SPARE_DI_002 | DI | Spare | NULL | NULL | **True** |
| DO_001 | DO | Output | NULL | NULL | False |
| ... | | | | | |

### After Assignment

| PID_TAG | IO_TYPE | SIGNAL_TYPE | MODULE_NUMBER | CHANNEL_NUMBER | is_wired_spare |
|---------|---------|-------------|---------------|----------------|----------------|
| DI_001 | DI | Input | 1 | 1 | False |
| DI_002 | DI | Input | 1 | 2 | False |
| ... | | | | | |
| WIRED_SPARE_DI_001 | DI | Spare | **3** | **1** | **True** |
| WIRED_SPARE_DI_002 | DI | Spare | **3** | **2** | **True** |
| DO_001 | DO | Output | 1 | 1 | False |
| ... | | | | | |

---

## Code Skeleton

### Method 1: calculate_wired_spares_needed()

```python
def calculate_wired_spares_needed(self, df_instruments):
    """Pre-calculate wired spares needed per IO type"""
    
    wired_spare_config = self.read_wired_spares_config()
    signal_counts = df_instruments['IO_TYPE'].value_counts().to_dict()
    
    results = {}
    for io_type in ['DI', 'DO', 'AI', 'AO']:
        signal_count = signal_counts.get(io_type, 0)
        if signal_count == 0:
            results[io_type] = {
                'total_signals': 0,
                'wired_spares_needed': 0,
                'total_items': 0,
                'modules_required': 0,
                'total_empty_channels': 0,
                'empty_channels_per_module': 0,
                'modules_with_extra_empty': 0
            }
            continue
        
        spare_factor = wired_spare_config.get(io_type, {}).get('spare_factor', 0)
        wired_spares = math.ceil(signal_count * spare_factor)
        total_items = signal_count + wired_spares
        modules_needed = math.ceil(total_items / 16)
        empty_channels = (modules_needed * 16) - total_items
        
        results[io_type] = {
            'total_signals': signal_count,
            'wired_spares_needed': wired_spares,
            'total_items': total_items,
            'modules_required': modules_needed,
            'total_empty_channels': empty_channels,
            'empty_channels_per_module': empty_channels // modules_needed if modules_needed > 0 else 0,
            'modules_with_extra_empty': empty_channels % modules_needed if modules_needed > 0 else 0
        }
    
    return results
```

### Method 2: inject_synthetic_wired_spares()

```python
def inject_synthetic_wired_spares(self, df_instruments, spare_calculations):
    """Create and inject synthetic wired spare rows"""
    
    synthetic_spares_list = []
    spare_counters = {io_type: 0 for io_type in ['DI', 'DO', 'AI', 'AO']}
    
    for io_type, calc in spare_calculations.items():
        for i in range(calc['wired_spares_needed']):
            spare_tag = f"WIRED_SPARE_{io_type}_{spare_counters[io_type]:03d}"
            spare_counters[io_type] += 1
            
            synthetic_spares_list.append({
                'PID_TAG': spare_tag,
                'IO_TYPE': io_type,
                'SIGNAL_TYPE': 'Spare',
                'MODULE_NUMBER': None,
                'CHANNEL_NUMBER': None,
                'is_wired_spare': True,
                # Add other columns with defaults...
            })
    
    if synthetic_spares_list:
        df_synthetic = pd.DataFrame(synthetic_spares_list)
        df_instruments = pd.concat([df_instruments, df_synthetic], ignore_index=True)
    
    return df_instruments
```

### Method 3: Modified assign_modules_intelligent()

```python
def assign_modules_intelligent(self, wired_spare_calculations=None):
    """Unified assignment of signals + spares"""
    
    if wired_spare_calculations is None:
        # Fallback for backward compatibility
        wired_spare_calculations = self.calculate_wired_spares_needed(self.df_instruments)
    
    for io_type in ['DI', 'DO', 'AI', 'AO']:
        items = self.df_instruments[
            self.df_instruments['IO_TYPE'] == io_type
        ].copy()
        
        if len(items) == 0:
            continue
        
        calc = wired_spare_calculations[io_type]
        
        # Get indices for both signals and spares
        signal_indices = items[items.get('is_wired_spare', False) == False].index.tolist()
        spare_indices = items[items.get('is_wired_spare', False) == True].index.tolist()
        
        # Combined assignment order: signals first, then spares
        all_indices = signal_indices + spare_indices
        
        module_num = 1
        channel_num = 1
        
        for idx in all_indices:
            self.df_instruments.loc[idx, 'MODULE_NUMBER'] = module_num
            self.df_instruments.loc[idx, 'CHANNEL_NUMBER'] = channel_num
            
            channel_num += 1
            if channel_num > 16:
                module_num += 1
                channel_num = 1
    
    return True
```

---

## Validation Checklist

After implementation:
- [ ] No overlapping channel assignments
- [ ] All signals assigned
- [ ] All synthetic spares assigned
- [ ] Module count matches calculation
- [ ] Empty channels tracked correctly
- [ ] Test with various IO type combinations
- [ ] Test with 0 signals per type
- [ ] Test with large signal counts (100+)

---

## Debugging Tips

1. **Verify spare count**: 
   ```python
   calc = calculate_wired_spares_needed(df)
   total_spares = sum(c['wired_spares_needed'] for c in calc.values())
   ```

2. **Check injection**:
   ```python
   synthetic_count = df[df['is_wired_spare'] == True].shape[0]
   assert synthetic_count == total_spares
   ```

3. **Verify assignment**:
   ```python
   unassigned = df[df['MODULE_NUMBER'].isna()].shape[0]
   assert unassigned == 0
   ```

4. **Check overlaps**:
   ```python
   for io_type in ['DI', 'DO', 'AI', 'AO']:
       for mod in range(1, max_modules + 1):
           channels = df[(df['IO_TYPE'] == io_type) & 
                        (df['MODULE_NUMBER'] == mod)]['CHANNEL_NUMBER'].tolist()
           assert len(channels) == len(set(channels))  # No duplicates
   ```

---

## Performance Considerations

- No performance issues expected
- Operations are O(n) where n = total instruments
- DataFrame concatenation (pd.concat) is efficient for this data scale
- Pre-calculation done once per run

---

## Backward Compatibility

- Old code checking for `is_wired_spare` column will work
- Synthetic spares use existing naming convention
- Can run old `generate_wired_spares()` in parallel during transition
- Safe to deprecate after 1-2 version cycles
