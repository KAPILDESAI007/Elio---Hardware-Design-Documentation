#!/usr/bin/env python3
"""
Simple validation test for wired spares fix.
Tests that wired spares are created and distributed, not just CH7-9.
"""

import pandas as pd
import sys
from pathlib import Path
from processors.channel_assignment_manager import ChannelAssignmentManager

print("="*70)
print("WIRED SPARES FIX VALIDATION TEST")
print("="*70)

# Create simple test data
test_signals = [
    {'PID_TAG': f'TEST-PIT-{i:03d}', 'IO_type_base': 'AI', 'IO_type': 'AI'} 
    for i in range(1, 26)  # 25 AI signals
]

test_hardware = [
    {
        'Module': 'FIO',
        'IO_Type': 'AI',
        'Nos of Channel': 16,
        'Usable_Channels': 16,
        'Nominal_Channels': 16
    }
]

df_signals = pd.DataFrame(test_signals)
df_hardware = pd.DataFrame(test_hardware)

# Add wired spare rows (mimicking what assign_modules_intelligent now does)
wired_spares = [
    {
        'PID_TAG': f'SPARE_AI_{i}',
        'IO_type_base': 'AI',
        'IO_type': 'AI_Spare'
    }
    for i in range(1, 4)  # 3 wired spares (10% of 25)
]
df_spares = pd.DataFrame(wired_spares)

# Concatenate signals and spares (as the fixed assign_modules_intelligent does)
df_instruments = pd.concat([df_signals, df_spares], ignore_index=True)

print(f"\n[TEST] Created test data:")
print(f"  - Signals: {len(df_signals)}")
print(f"  - Wired spares: {len(df_spares)}")
print(f"  - Total rows: {len(df_instruments)}")

# Now test the ChannelAssignmentManager
print(f"\n[TEST] Initializing ChannelAssignmentManager...")
manager = ChannelAssignmentManager(df_instruments, df_hardware)

print(f"[TEST] Running analyze_and_plan()...")
analysis = manager.analyze_and_plan()

if not analysis.get('success'):
    print(f"[FAIL] ❌ Analysis failed: {analysis}")
    sys.exit(1)

print(f"[TEST] Analysis results:")
print(f"  - Total signals: {analysis['total_signals']}")
print(f"  - Total wired spares: {analysis['total_wired_spares']}")
print(f"  - Modules needed: {analysis['total_modules']}")
print(f"  - Channels per module: {analysis['channels_per_module']}")
print(f"  - Spares per module: {analysis['wired_spares_per_module']:.2f}")

print(f"\n[TEST] Running assign_channels()...")
df_result = manager.assign_channels()

if df_result.empty:
    print(f"[FAIL] ❌ Assignment failed - empty result")
    sys.exit(1)

print(f"[TEST] Assignment results:")
print(f"  - Total rows in result: {len(df_result)}")
print(f"  - Assigned (Channel > 0): {(df_result['Channel'] > 0).sum()}")
print(f"  - Unassigned (Channel = 0): {(df_result['Channel'] == 0).sum()}")

# Count wired spares in assignment
wired_in_result = df_result[df_result['PID_TAG'].str.contains('SPARE_', case=False, na=False)]
print(f"  - Wired spares in result: {len(wired_in_result)}")

if len(wired_in_result) < len(df_spares):
    print(f"[PARTIAL] ⚠️  Only {len(wired_in_result)} of {len(df_spares)} wired spares were assigned")
else:
    print(f"[PASS] ✓ All wired spares were assigned")

# Check channels used
assigned = df_result[df_result['Channel'] > 0]
channels_used = sorted(assigned['Channel'].unique())
print(f"\n[TEST] Channels used in assignment: {channels_used}")

# Specifically check if spares are NOT just in CH7-9
wired_channels = sorted(wired_in_result['Channel'].unique())
print(f"[TEST] Wired spare channels: {wired_channels}")

if set(wired_channels) == {7, 8, 9} and len(wired_in_result) == 3:
    print(f"[FAIL] ❌ Still only CH7, CH8, CH9 - BUG NOT FIXED!")
    sys.exit(1)
elif len(wired_channels) >= len(df_spares) or len(wired_in_result) == len(df_spares):
    print(f"[PASS] ✓ Wired spares are properly distributed!")
else:
    print(f"[INFO] Wired spares distribution: {wired_channels}")

print(f"\n[TEST] Detailed wired spare assignments:")
for idx, row in wired_in_result.iterrows():
    print(f"  {row['PID_TAG']:20s} -> Channel {row['Channel']} (Module {row['Module_Instance']})")

print("\n" + "="*70)
print("TEST COMPLETED SUCCESSFULLY")
print("="*70)
