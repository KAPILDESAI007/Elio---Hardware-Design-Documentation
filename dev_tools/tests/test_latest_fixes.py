#!/usr/bin/env python
"""Test the fixes for DO/DI-RL assignment and IO Card Summary"""

import pandas as pd
from pathlib import Path

# Read the latest output
output_file = Path('Design Input Review_2026-01-25.xlsx')

print("\n" + "="*100)
print("TESTING FIXES")
print("="*100)

if output_file.exists():
    # Read assigned sheet
    df_assigned = pd.read_excel(output_file, sheet_name='Assigned')
    
    # Check IO types
    print("\n[TEST 1] IO Type Normalization (DI-RL → DI, DO-R → DO)")
    print("-" * 100)
    print(f"Unique IO types in assigned: {df_assigned['IO_type'].unique()}")
    print(f"\nSample DO and DI assignments:")
    do_signals = df_assigned[df_assigned['IO_type'] == 'DO'].head(10)
    print(do_signals[['PID_TAG', 'IO_type', 'Module_Name', 'Slot', 'Node']].to_string() if len(do_signals) > 0 else "No DO signals found")
    
    di_rl_signals = df_assigned[df_assigned['IO_type'].str.contains('DI-RL', na=False)].head(10)
    print(f"\nDI-RL signals in assigned: {len(di_rl_signals)}")
    
    # Check redundancy slots
    print("\n[TEST 2] Redundancy Slot Allocation")
    print("-" * 100)
    print("Checking for signals on Slot-2, Slot-4, etc when Slot-1, Slot-3 are redundant...")
    
    # Check if redundancy flag is set
    if 'Redundancy_Flag' in df_assigned.columns:
        redundant_signals = df_assigned[df_assigned['Redundancy_Flag'] == 'Yes']
        print(f"\nRedundant signals: {len(redundant_signals)}")
        
        # Group by Module_Name and Slot to see which slots have signals
        print("\nModule instances and their slot assignments:")
        for module in df_assigned[df_assigned['Module_Name'] != '']['Module_Name'].unique()[:5]:
            module_data = df_assigned[df_assigned['Module_Name'] == module][['PID_TAG', 'Module_Name', 'Slot', 'Redundancy_Flag']].drop_duplicates()
            if len(module_data) > 0:
                print(f"\n{module}:")
                print(module_data.to_string(index=False))
    
    # Check IO Card Summary
    print("\n[TEST 3] IO Card Summary Format")
    print("-" * 100)
    try:
        df_summary = pd.read_excel(output_file, sheet_name='Summary')
        print("Summary sheet exists - checking structure...")
        # The summary may not have the IO Card in the expected format in this file
    except:
        print("No Summary sheet with IO Card")
    
    # Check unassigned
    print("\n[TEST 4] Unassigned Signals")
    print("-" * 100)
    try:
        df_unassigned = pd.read_excel(output_file, sheet_name='Unassigned')
        print(f"Total unassigned: {len(df_unassigned)}")
        print(f"\nUnassigned IO types:")
        print(df_unassigned['IO_type'].value_counts())
        
        # Check if DO and DI-RL are still unassigned
        do_unassigned = len(df_unassigned[df_unassigned['IO_type'] == 'DO'])
        di_rl_unassigned = len(df_unassigned[df_unassigned['IO_type'] == 'DI-RL'])
        print(f"\nDO signals unassigned: {do_unassigned}")
        print(f"DI-RL signals unassigned: {di_rl_unassigned}")
    except:
        print("No unassigned sheet")

else:
    print(f"Output file not found: {output_file}")

print("\n" + "="*100 + "\n")
