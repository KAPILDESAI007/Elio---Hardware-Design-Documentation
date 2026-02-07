#!/usr/bin/env python3
"""
Test script to verify wired spares are properly distributed to ALL channels,
not just CH7-9 in slot-3.
"""

import pandas as pd
from Design Input Review import DesignInputReview
from pathlib import Path

# Create a test instance
print("="*70)
print("Testing Wired Spares Distribution FIX")
print("="*70)

reviewer = DesignInputReview()
reviewer.project_dir = Path.cwd()

# Set basic parameters
reviewer.wired_spares_percentage = 10  # 10% wired spares
reviewer.controller_model = 'ProSafe SIS Series'
reviewer.temperature_rating = 'Standard'
reviewer.explosion_protection = 'No'
reviewer.io_types = ['FIO']
reviewer.system_type = 'Safety'
reviewer.redundancy_types = ['AI', 'DI', 'DO']
reviewer.is_types = ['AI', 'DI', 'DO']

# Load input file
instrument_file = list(Path('uploads').glob('design_input_*.xls*'))
if not instrument_file:
    print(f"[ERROR] No test files found in uploads/")
    exit(1)

# Use the most recent file
instrument_file = sorted(instrument_file)[-1]
print(f"[INFO] Using test file: {instrument_file}")

# Read the file
reviewer.instrument_file = instrument_file
if not reviewer.read_instrument_file():
    print("[ERROR] Failed to read instrument file")
    exit(1)

if not reviewer.extract_required_columns():
    print("[ERROR] Failed to extract columns")
    exit(1)

if not reviewer.apply_user_inputs():
    print("[ERROR] Failed to apply user inputs")
    exit(1)

if not reviewer.sort_by_pid_tag():
    print("[ERROR] Failed to sort by PID_TAG")
    exit(1)

if not reviewer.read_hardware_config():
    print("[ERROR] Failed to read hardware config")
    exit(1)

print("\n[DEBUG] Before assign_modules_intelligent:")
print(f"  - df_instruments rows: {len(reviewer.df_instruments)}")
print(f"  - Unique IO_type_base: {reviewer.df_instruments['IO_type_base'].unique()}")

# This is the key test - call the fixed method
if not reviewer.assign_modules_intelligent():
    print("[ERROR] Failed to assign modules intelligently")
    exit(1)

print("\n[DEBUG] After assign_modules_intelligent:")
print(f"  - df_assigned rows: {len(reviewer.df_assigned)}")

# Count wired spares in assignment
wired_spares_assigned = reviewer.df_assigned[
    reviewer.df_assigned['PID_TAG'].str.contains('SPARE_', case=False, na=False)
]
print(f"  - Wired spares assigned: {len(wired_spares_assigned)}")

# Count by IO type
for io_type in reviewer.df_assigned['IO_type_base'].unique():
    if pd.isna(io_type):
        continue
    count = len(reviewer.df_assigned[reviewer.df_assigned['IO_type_base'] == io_type])
    assigned_count = len(reviewer.df_assigned[
        (reviewer.df_assigned['IO_type_base'] == io_type) & 
        (reviewer.df_assigned['Channel'] > 0)
    ])
    print(f"    {io_type}: {assigned_count} assigned / {count} total")

# Check channels are distributed across modules
assigned_with_channel = reviewer.df_assigned[reviewer.df_assigned['Channel'] > 0].copy()
print(f"\n[DEBUG] Channel distribution:")
for module_instance in sorted(assigned_with_channel['Module_Instance'].unique()):
    if module_instance == '':
        continue
    module_data = assigned_with_channel[assigned_with_channel['Module_Instance'] == module_instance]
    channels = sorted(module_data['Channel'].unique())
    print(f"  {module_instance}: channels {channels} ({len(channels)} total)")

# Verify wired spares are NOT just in CH7-9
print(f"\n[TEST] Verifying wired spares distribution:")
wired_spare_channels = wired_spares_assigned['Channel'].unique()
print(f"  - Wired spare channels: {sorted(wired_spare_channels)}")

# Check for the specific issue: only CH7,8,9
if set(wired_spare_channels) == {7, 8, 9}:
    print("[FAIL] ❌ Still only CH7, CH8, CH9 - BUG NOT FIXED!")
    exit(1)
elif len(wired_spare_channels) == 3 and min(wired_spare_channels) == 7:
    print("[FAIL] ❌ Still only 3 consecutive channels starting from CH7 - BUG NOT FIXED!")
    exit(1)
elif len(wired_spare_channels) >= len(reviewer.wired_spares_count):
    print("[PASS] ✓ Wired spares are distributed properly!")
    print(f"  - Expected ~{sum(reviewer.wired_spares_count.values())} spares")
    print(f"  - Got {len(wired_spares_assigned)} spares across channels: {sorted(wired_spare_channels)}")
else:
    print(f"[PARTIAL] ⚠️  Got {len(wired_spares_assigned)} wired spares")
    print(f"  - Channels: {sorted(wired_spare_channels)}")

print("\n" + "="*70)
print("Test Complete")
print("="*70)
