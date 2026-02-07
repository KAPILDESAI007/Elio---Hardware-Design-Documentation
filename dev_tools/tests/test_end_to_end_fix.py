#!/usr/bin/env python3
"""
End-to-end test of the wired spares fix using actual input file.
"""

import pandas as pd
from pathlib import Path
import sys
import importlib.util

# Import Design Input Review with spaces in filename
spec = importlib.util.spec_from_file_location("DesignInputReview", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

print("="*70)
print("END-TO-END WIRED SPARES FIX TEST")
print("="*70)

# Find latest input file
input_files = list(Path('uploads').glob('*.xls*'))
if not input_files:
    print("[ERROR] No input files found")
    sys.exit(1)

input_file = sorted(input_files)[-1]
print(f"\n[INFO] Using input file: {input_file.name}")

# Create reviewer
reviewer = DesignInputReview()
reviewer.project_dir = Path.cwd()  # Set project directory
reviewer.instrument_file = input_file  # This is the actual file path
reviewer.wired_spares_percentage = 10  # 10% wired spares
reviewer.temperature_rating = 'Standard'
reviewer.explosion_protection = 'No'

# Run the workflow steps
print("\n[STEP 1] Read instrument file...")
if not reviewer.read_instrument_file():
    print("[ERROR] Failed")
    sys.exit(1)
print(f"  - Read {len(reviewer.df_instruments)} rows")

print("\n[STEP 2] Extract required columns...")
if not reviewer.extract_required_columns():
    print("[ERROR] Failed")
    sys.exit(1)
print(f"  - Extracted columns from {len(reviewer.df_instruments)} rows")

print("\n[STEP 3] Apply user inputs...")
if not reviewer.apply_user_inputs():
    print("[ERROR] Failed")
    sys.exit(1)

print("\n[STEP 4] Sort by PID_TAG...")
if not reviewer.sort_by_pid_tag():
    print("[ERROR] Failed")
    sys.exit(1)

print("\n[STEP 5] Read hardware config...")
if not reviewer.read_hardware_config():
    print("[ERROR] Failed")
    sys.exit(1)
print(f"  - Loaded {len(reviewer.df_hardware)} hardware configs")

print("\n[STEP 6] Assign modules intelligently...")
print(f"  - Before: {len(reviewer.df_instruments)} instruments")
if not reviewer.assign_modules_intelligent():
    print("[ERROR] Failed")
    sys.exit(1)
print(f"  - After: {len(reviewer.df_assigned)} assigned")

# Check what was assigned
assigned_count = (reviewer.df_assigned['Channel'] > 0).sum()
wired_spares = reviewer.df_assigned[reviewer.df_assigned['PID_TAG'].str.contains('SPARE_', case=False, na=False)]
print(f"  - Assigned items: {assigned_count}")
print(f"  - Wired spares: {len(wired_spares)}")

# Check channels in slot 3
slot3_items = reviewer.df_assigned[
    (reviewer.df_assigned['Slot'] == 3) & 
    (reviewer.df_assigned['Module_Instance'] != "")
]
if not slot3_items.empty:
    print(f"\n[ANALYSIS] Slot 3 assignments:")
    print(f"  - Total items in slot 3: {len(slot3_items)}")
    slot3_channels = sorted(slot3_items[slot3_items['Channel'] > 0]['Channel'].unique())
    print(f"  - Channels used: {slot3_channels}")
    
    # Check for the specific issue
    slot3_wired = slot3_items[slot3_items['PID_TAG'].str.contains('SPARE_', case=False, na=False)]
    if not slot3_wired.empty:
        wired_channels = sorted(slot3_wired['Channel'].unique())
        print(f"  - Wired spare channels in slot 3: {wired_channels}")
        
        if set(wired_channels) == {7, 8, 9} and len(slot3_wired) == 3:
            print(f"  - ⚠️  WARNING: Still only CH7, CH8, CH9 in slot 3!")
        elif len(wired_channels) >= 3:
            print(f"  - ✓ Wired spares are distributed across {len(wired_channels)} channels")
else:
    print("\n[INFO] No items assigned to slot 3 yet (will be assigned later)")

print("\n[STEP 7] Read FIO configuration...")
if not reviewer.read_fio_config():
    print("[ERROR] Failed")
    sys.exit(1)

print("\n[STEP 8] Assign nodes and controllers...")
if not reviewer.assign_nodes_and_controllers():
    print("[ERROR] Failed")
    sys.exit(1)

print("\n[STEP 9] Identify unassigned...")
if not reviewer.identify_unassigned():
    print("[ERROR] Failed")
    sys.exit(1)

print("\n[FINAL] Generate output file...")
if not reviewer.generate_output_file():
    print("[ERROR] Failed")
    sys.exit(1)

# Check the output file
output_files = list(Path.cwd().glob('Design Input Review_*.xlsx'))
if output_files:
    output_file = sorted(output_files)[-1]
    print(f"  - Generated: {output_file.name}")
    
    # Read the output to verify
    assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
    print(f"  - Assigned sheet: {len(assigned_df)} rows")
    
    # Check slot 3 in output
    slot3_output = assigned_df[assigned_df['Slot'] == 3]
    if not slot3_output.empty:
        print(f"\n[VERIFICATION] Output file - Slot 3:")
        print(f"  - Total items: {len(slot3_output)}")
        slot3_channels_out = sorted(slot3_output[pd.to_numeric(slot3_output['Channel'], errors='coerce') > 0]['Channel'].unique())
        print(f"  - Channels: {[int(c) for c in slot3_channels_out if pd.notna(c)]}")
        
        # Check for wired spares pattern
        slot3_wired_out = slot3_output[slot3_output['PID_TAG'].str.contains('SCS.*_N1S3CH', regex=True, na=False)]
        if not slot3_wired_out.empty:
            wired_out_channels = [int(row.split('CH')[1]) if 'CH' in row else 0 
                                  for row in slot3_wired_out['PID_TAG'].tolist()]
            print(f"  - Wired spares (pattern SCS*_N1S3CH*): {sorted(wired_out_channels)}")

print("\n" + "="*70)
print("TEST COMPLETED")
print("="*70)
