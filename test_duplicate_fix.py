#!/usr/bin/env python3
"""Test the duplicate channel prevention logic"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import importlib.util
import pandas as pd
from pathlib import Path

# Load the module with spaces in its name
spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

# Create instance and test
print("Testing duplicate prevention logic...")
reviewer = DesignInputReview()

# Load the latest test file
test_file = 'Design Input Review_2026-01-31.xlsx'
try:
    reviewer.df_instruments = pd.read_excel(test_file)
    print(f"[OK] Loaded {test_file}")
except Exception as e:
    print(f"[FAILED] Failed to load {test_file}: {e}")
    sys.exit(1)

try:
    if not reviewer.extract_required_columns():
        print("✗ Failed to extract required columns")
        sys.exit(1)
    print("✓ Extracted required columns")
except Exception as e:
    print(f"✗ Extract failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    if not reviewer.apply_user_inputs():
        print("✗ Failed to apply user inputs")
        sys.exit(1)
    print("✓ Applied user inputs")
except Exception as e:
    print(f"✗ Apply user inputs failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    if not reviewer.sort_by_pid_tag():
        print("✗ Failed to sort")
        sys.exit(1)
    print("✓ Sorted by PID tag")
except Exception as e:
    print(f"✗ Sort failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    if not reviewer.read_hardware_config():
        print("✗ Failed to read hardware")
        sys.exit(1)
    print("✓ Read hardware config")
except Exception as e:
    print(f"✗ Read hardware failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    if not reviewer.read_mounting_rule():
        print("✗ Failed to read mounting rule")
        sys.exit(1)
    print("✓ Read mounting rule")
except Exception as e:
    print(f"✗ Read mounting rule failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    if not reviewer.read_controller_limits():
        print("✗ Failed to read controller limits")
        sys.exit(1)
    print("✓ Read controller limits")
except Exception as e:
    print(f"✗ Read controller limits failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# THIS IS THE KEY TEST - the original assign_modules (now with duplicate prevention)
try:
    if not reviewer.assign_modules():
        print("✗ Failed to assign modules")
        sys.exit(1)
    print("✓ Assigned modules")
except Exception as e:
    print(f"✗ Assign modules failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Analyze results
assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
print(f'\n=== ASSIGNMENT RESULTS ===')
print(f'Total instruments: {len(reviewer.df_assigned)}')
print(f'Total assigned: {len(assigned)}')
print(f'Unassigned: {len(reviewer.df_assigned) - len(assigned)}')

# Check for duplicates - the key validation
print(f'\n=== DUPLICATE CHECK ===')
duplicates = assigned.groupby(['Module_Instance', 'Channel']).size()
duplicate_count = (duplicates > 1).sum()

if duplicate_count == 0:
    print(f"[OK] NO DUPLICATES FOUND - Each channel assigned to only 1 signal")
else:
    print(f"[ERROR] DUPLICATES FOUND: {duplicate_count} (Module_Instance, Channel) pairs have multiple signals")
    print("\nDuplicate assignments:")
    for (instance, channel), count in duplicates[duplicates > 1].items():
        tags = assigned[(assigned['Module_Instance'] == instance) & (assigned['Channel'] == channel)]['PID_TAG'].tolist()
        print(f"  {instance}, Channel {channel}: {count} tags = {tags}")

# Show channel distribution
print(f'\n=== CHANNEL DISTRIBUTION ===')
for instance in sorted(assigned['Module_Instance'].unique()):
    instance_data = assigned[assigned['Module_Instance'] == instance]
    channels = sorted(instance_data['Channel'].unique())
    print(f'{instance}: Channels {channels} ({len(channels)} channels used, {len(instance_data)} signals)')

# Detailed check on first AI instance
print(f'\n=== DETAILED CHANNEL-1 CHECK ===')
ai_channels_1 = assigned[(assigned['Module_Instance'].str.contains('AI')) & (assigned['Channel'] == 1)]
print(f'Signals assigned to Channel 1: {len(ai_channels_1)}')
if len(ai_channels_1) > 1:
    print("[ERROR] PROBLEM: Multiple signals on Channel 1:")
    for idx, row in ai_channels_1.iterrows():
        print(f"  - {row['PID_TAG']}")
elif len(ai_channels_1) == 1:
    print(f"[OK] Only 1 signal on Channel 1: {ai_channels_1.iloc[0]['PID_TAG']}")
else:
    print("[OK] No signals on Channel 1")

