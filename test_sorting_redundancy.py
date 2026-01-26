#!/usr/bin/env python3
"""Diagnose sorting and redundancy issues"""

import pandas as pd
import os
import glob

# Find the most recent output file
output_files = glob.glob('Design Input Review_*.xlsx')
if output_files:
    output_file = sorted(output_files)[-1]  # Get the most recent one
    print(f"Found output file: {output_file}")
else:
    print("[ERROR] No output file found")
    exit(1)

if os.path.exists(output_file):
    print("=" * 60)
    print("TESTING SORTING AND REDUNDANCY")
    print("=" * 60)
    
    # Read Assigned sheet
    try:
        assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
        print(f"\n[TEST 1] ASSIGNED SHEET - First 20 rows (checking Slot/Node sort):")
        print(f"Total rows: {len(assigned_df)}")
        print("\nColumns:", assigned_df.columns.tolist())
        
        if 'Slot' in assigned_df.columns and 'Node' in assigned_df.columns:
            # Show first 20 rows with relevant columns
            display_cols = ['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'Module_Name', 'Slot', 'Node', 'Channel', 'Redundancy_Flag']
            display_cols = [c for c in display_cols if c in assigned_df.columns]
            
            print("\n" + assigned_df[display_cols].head(20).to_string())
            
            # Check if sorted
            print("\n[CHECK] Sorting verification:")
            assigned_df['Slot_num'] = pd.to_numeric(assigned_df['Slot'], errors='coerce')
            assigned_df['Node_num'] = pd.to_numeric(assigned_df['Node'], errors='coerce')
            
            # Check sorting
            is_sorted = True
            for i in range(len(assigned_df) - 1):
                slot_i = assigned_df['Slot_num'].iloc[i]
                slot_next = assigned_df['Slot_num'].iloc[i + 1]
                node_i = assigned_df['Node_num'].iloc[i]
                node_next = assigned_df['Node_num'].iloc[i + 1]
                
                if pd.isna(slot_i) or pd.isna(slot_next):
                    continue
                
                if slot_i < slot_next:
                    continue  # Good
                elif slot_i == slot_next and node_i <= node_next:
                    continue  # Good
                else:
                    is_sorted = False
                    print(f"  [ERROR] Row {i}: Slot {slot_i} Node {node_i} vs Row {i+1}: Slot {slot_next} Node {node_next}")
                    if i < 5:
                        break
            
            if is_sorted:
                print("  ✓ Data is properly sorted by Slot, then Node")
            else:
                print("  ✗ Sorting is NOT correct")
                
                # Show the unsorted data
                print("\nShowing raw data order (no sorting):")
                print(assigned_df[['PID_TAG', 'Slot_num', 'Node_num']].head(20).to_string())
        
        # Check Redundancy_Flag values
        print("\n[TEST 2] REDUNDANCY FLAG VALUES:")
        if 'Redundancy_Flag' in assigned_df.columns:
            print("\nUnique Redundancy_Flag values:")
            print(assigned_df['Redundancy_Flag'].value_counts(dropna=False))
            
            # Show some DI-RL signals
            if 'IO_type' in assigned_df.columns:
                di_rl_assigned = assigned_df[assigned_df['IO_type'].str.contains('DI-RL', na=False)]
                if len(di_rl_assigned) > 0:
                    print(f"\nDI-RL signals in ASSIGNED sheet: {len(di_rl_assigned)}")
                    print(di_rl_assigned[display_cols].head(10).to_string())
                else:
                    print("\nNo DI-RL signals in ASSIGNED sheet")
        
    except Exception as e:
        print(f"[ERROR] Reading Assigned sheet: {e}")
        import traceback
        traceback.print_exc()
    
    # Read Unassigned sheet
    try:
        unassigned_df = pd.read_excel(output_file, sheet_name='Unassigned')
        print(f"\n[TEST 3] UNASSIGNED SHEET - Checking DI-RL signals:")
        print(f"Total unassigned rows: {len(unassigned_df)}")
        
        if 'IO_type' in unassigned_df.columns:
            di_rl_unassigned = unassigned_df[unassigned_df['IO_type'].str.contains('DI-RL', na=False)]
            print(f"\nDI-RL signals in UNASSIGNED sheet: {len(di_rl_unassigned)}")
            
            display_cols = ['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'Redundancy_Flag', 'Slot', 'Node']
            display_cols = [c for c in display_cols if c in unassigned_df.columns]
            
            if len(di_rl_unassigned) > 0:
                print("\nFirst 10 unassigned DI-RL signals:")
                print(di_rl_unassigned[display_cols].head(10).to_string())
                
                # Check Redundancy_Flag
                print(f"\nUnique Redundancy_Flag values in DI-RL unassigned:")
                print(di_rl_unassigned['Redundancy_Flag'].value_counts(dropna=False))
        
        # Count unassigned by type
        if 'IO_type' in unassigned_df.columns:
            print(f"\n[TEST 4] UNASSIGNED BY TYPE:")
            print(unassigned_df['IO_type'].value_counts().to_string())
        
    except Exception as e:
        print(f"[ERROR] Reading Unassigned sheet: {e}")
        import traceback
        traceback.print_exc()

else:
    print(f"[ERROR] Output file not found: {output_file}")
    print("Please run the tool first to generate the output file")
