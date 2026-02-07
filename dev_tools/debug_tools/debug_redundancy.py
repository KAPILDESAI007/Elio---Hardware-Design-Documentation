#!/usr/bin/env python
"""Debug script to check IO_REDUNDANCY column"""

import pandas as pd
from pathlib import Path

# Read the latest output
output_file = Path('Design Input Review_2026-01-25.xlsx')

if output_file.exists():
    df_assigned = pd.read_excel(output_file, sheet_name='Assigned')
    
    print("\n" + "="*100)
    print("Checking Redundancy_Flag column")
    print("="*100)
    
    # Check if Redundancy_Flag exists and what values it has
    if 'Redundancy_Flag' in df_assigned.columns:
        print(f"\nRedundancy_Flag value counts:")
        print(df_assigned['Redundancy_Flag'].value_counts(dropna=False))
        
        print(f"\nSample rows with values:")
        print(df_assigned[['PID_TAG', 'IO_type', 'Module_Name', 'Redundancy_Flag']].head(30).to_string())
    
    # Check what the assigned signals should have as redundancy
    print("\n" + "="*100)
    print("Sample unassigned signals (to see what redundancy they should have)")
    print("="*100)
    
    try:
        df_unassigned = pd.read_excel(output_file, sheet_name='Unassigned')
        # Show DO and DI-RL signals
        do_signals = df_unassigned[df_unassigned['IO_type'] == 'DO'].head(10)
        di_rl_signals = df_unassigned[df_unassigned['IO_type'] == 'DI-RL'].head(10)
        
        print("\nDO unassigned samples:")
        if len(do_signals) > 0:
            print(do_signals[['PID_TAG', 'IO_type', 'IO_REDUNDANCY' if 'IO_REDUNDANCY' in do_signals.columns else 'N/A']].to_string())
        
        print("\nDI-RL unassigned samples:")
        if len(di_rl_signals) > 0:
            print(di_rl_signals[['PID_TAG', 'IO_type']].head().to_string())
    except Exception as e:
        print(f"Error reading unassigned: {e}")

else:
    print(f"Output file not found: {output_file}")
