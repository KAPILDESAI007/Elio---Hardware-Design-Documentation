#!/usr/bin/env python3
"""Detailed diagnostic for 494-HS-459A and sorting verification"""

import pandas as pd
import os
import glob

# Find the most recent output file
output_files = glob.glob('Design Input Review_*.xlsx')
if not output_files:
    print("[ERROR] No output file found")
    exit(1)

output_file = sorted(output_files)[-1]
print(f"Testing file: {output_file}\n")

# ====================
# TEST 1: Find 494-HS-459A
# ====================
print("=" * 70)
print("TEST 1: Finding signal 494-HS-459A")
print("=" * 70)

try:
    assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
    unassigned_df = pd.read_excel(output_file, sheet_name='Unassigned')
    
    # Search for the signal
    signal_tag = '494-HS-459A'
    
    in_assigned = assigned_df[assigned_df['PID_TAG'] == signal_tag]
    in_unassigned = unassigned_df[unassigned_df['PID_TAG'] == signal_tag]
    
    print(f"\nSearching for: {signal_tag}")
    
    if len(in_assigned) > 0:
        print(f"✓ Found in ASSIGNED sheet:")
        cols = ['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'Module_Name', 'Slot', 'Node', 'Channel', 'Redundancy_Flag']
        cols = [c for c in cols if c in in_assigned.columns]
        print(in_assigned[cols].to_string())
    else:
        print(f"✗ NOT in Assigned sheet")
    
    if len(in_unassigned) > 0:
        print(f"✗ Found in UNASSIGNED sheet:")
        cols = ['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'Module_Name', 'Slot', 'Node', 'Channel', 'Redundancy_Flag']
        cols = [c for c in cols if c in in_unassigned.columns]
        print(in_unassigned[cols].to_string())
    else:
        print(f"✓ NOT in Unassigned sheet")
    
    # ====================
    # TEST 2: Sorting verification
    # ====================
    print("\n" + "=" * 70)
    print("TEST 2: Sorting Verification in ASSIGNED sheet")
    print("=" * 70)
    
    # Check if Slot and Node columns exist
    if 'Slot' not in assigned_df.columns or 'Node' not in assigned_df.columns:
        print("[ERROR] Slot or Node column not found")
    else:
        # Convert to numeric
        assigned_df_sorted = assigned_df.copy()
        assigned_df_sorted['Slot_num'] = pd.to_numeric(assigned_df_sorted['Slot'], errors='coerce')
        assigned_df_sorted['Node_num'] = pd.to_numeric(assigned_df_sorted['Node'], errors='coerce')
        
        # Show first 30 rows
        print("\nFirst 30 rows with Slot and Node:")
        display_cols = ['PID_TAG', 'IO_type', 'Slot_num', 'Node_num', 'Channel', 'Redundancy_Flag']
        print(assigned_df_sorted[display_cols].head(30).to_string())
        
        # Check actual sorting
        print("\n[SORT CHECK] Verifying order...")
        is_sorted = True
        sort_errors = []
        
        for i in range(len(assigned_df_sorted) - 1):
            slot_i = assigned_df_sorted['Slot_num'].iloc[i]
            slot_next = assigned_df_sorted['Slot_num'].iloc[i + 1]
            node_i = assigned_df_sorted['Node_num'].iloc[i]
            node_next = assigned_df_sorted['Node_num'].iloc[i + 1]
            
            if pd.isna(slot_i) or pd.isna(slot_next):
                continue
            
            # Check if properly sorted
            if slot_i < slot_next:
                continue  # Good, slot increased
            elif slot_i == slot_next:
                if node_i <= node_next:
                    continue  # Good, same slot but node increased or same
                else:
                    is_sorted = False
                    sort_errors.append(f"Row {i}: Slot {slot_i} Node {node_i} vs Row {i+1}: Slot {slot_next} Node {node_next}")
            else:
                is_sorted = False
                sort_errors.append(f"Row {i}: Slot {slot_i} vs Row {i+1}: Slot {slot_next} (SLOT DECREASED)")
        
        if is_sorted:
            print("✓ Data IS properly sorted by Slot (ascending), then Node (ascending)")
        else:
            print("✗ Sorting is BROKEN. Found errors:")
            for err in sort_errors[:5]:  # Show first 5 errors
                print(f"  - {err}")
    
    # ====================
    # TEST 3: DI-RL capacity analysis
    # ====================
    print("\n" + "=" * 70)
    print("TEST 3: DI-RL Capacity Analysis")
    print("=" * 70)
    
    # Count DI-RL signals by status
    all_data = pd.concat([assigned_df, unassigned_df])
    di_rl_all = all_data[all_data['IO_type'].str.contains('DI-RL', na=False)]
    
    di_rl_assigned = assigned_df[assigned_df['IO_type'].str.contains('DI-RL', na=False)]
    di_rl_unassigned = unassigned_df[unassigned_df['IO_type'].str.contains('DI-RL', na=False)]
    
    print(f"\nDI-RL Signal Count:")
    print(f"  Total: {len(di_rl_all)}")
    print(f"  Assigned: {len(di_rl_assigned)}")
    print(f"  Unassigned: {len(di_rl_unassigned)}")
    
    # Count by redundancy
    if 'IO_REDUNDANCY' in di_rl_all.columns:
        print(f"\nDI-RL Redundancy breakdown (all):")
        print(di_rl_all['IO_REDUNDANCY'].value_counts())
        
        assigned_red = di_rl_assigned[di_rl_assigned['IO_REDUNDANCY'] == 'Y']
        unassigned_red = di_rl_unassigned[di_rl_unassigned['IO_REDUNDANCY'] == 'Y']
        
        print(f"\nDI-RL with IO_REDUNDANCY='Y':")
        print(f"  Assigned: {len(assigned_red)}")
        print(f"  Unassigned: {len(unassigned_red)}")
    
    # Show capacity per SDV144-S instance
    print(f"\nSDV144-S (DI module) instances and usage:")
    assigned_modules = assigned_df[assigned_df['Module_Name'] == 'SDV144-S']
    if len(assigned_modules) > 0:
        module_usage = assigned_modules.groupby('Module_Instance').size()
        for instance, count in module_usage.items():
            print(f"  {instance}: {count} channels used")
    
    # ====================
    # TEST 4: Check if 494-HS-459A is in input data
    # ====================
    print("\n" + "=" * 70)
    print("TEST 4: Input Data Check for 494-HS-459A")
    print("=" * 70)
    
    # Try to read the input instruments file if available
    try:
        input_files = glob.glob('*.xls') + glob.glob('*.xlsx')
        input_files = [f for f in input_files if 'Design Input Review' not in f]
        
        if input_files:
            print(f"\nSearching in input files: {input_files}")
            for input_file in input_files[:3]:  # Check first 3 files
                try:
                    input_df = pd.read_excel(input_file, sheet_name='Instruments')
                    signal = input_df[input_df['PID_TAG'] == signal_tag]
                    if len(signal) > 0:
                        print(f"\nFound in {input_file}:")
                        signal_cols = ['PID_TAG', 'signal_origin', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS']
                        signal_cols = [c for c in signal_cols if c in signal.columns]
                        print(signal[signal_cols].to_string())
                except:
                    pass
    except Exception as e:
        print(f"Could not check input files: {e}")
        
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
