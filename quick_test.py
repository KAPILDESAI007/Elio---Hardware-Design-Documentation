#!/usr/bin/env python3
"""Simple test - just check if the new logic compiles and makes sense"""

import pandas as pd
import glob

print("Checking for existing output files...")
output_files = glob.glob('Design Input Review_*.xlsx')
if output_files:
    output_file = sorted(output_files)[-1]
    print(f"Using: {output_file}")
    
    try:
        assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
        print(f"\nTotal assigned signals: {len(assigned_df)}")
        
        # Check AI-R signals
        ai_r = assigned_df[assigned_df['IO_type'] == 'AI-R']
        print(f"AI-R signals: {len(ai_r)}")
        
        if len(ai_r) > 0:
            print("\nFirst 10 AI-R signals:")
            cols = ['PID_TAG', 'IO_REDUNDANCY', 'Node', 'Slot', 'Channel', 'Redundancy_Flag']
            cols = [c for c in cols if c in ai_r.columns]
            print(ai_r[cols].head(10).to_string())
            
            # Check channel pattern
            print("\nChecking channel allocation pattern...")
            ai_r_slot1 = ai_r[ai_r['Slot'] == 1]
            if len(ai_r_slot1) > 0:
                channels = sorted(ai_r_slot1['Channel'].tolist())
                print(f"Slot 1 channels: {channels}")
                
                # Expected odd channels
                expected = [1, 3, 5, 7, 9, 11, 13, 15]
                actual_odd = [c for c in channels if c % 2 == 1]
                
                if actual_odd == expected[:len(actual_odd)]:
                    print("SUCCESS: Channels are odd numbers (1, 3, 5, 7...)")
                else:
                    print(f"Issue: Got {actual_odd}, expected odd sequence {expected[:len(actual_odd)]}")
        
        # Check sorting
        print("\nChecking sorting (Node -> Slot -> Channel)...")
        assigned_df['N'] = pd.to_numeric(assigned_df['Node'], errors='coerce')
        assigned_df['S'] = pd.to_numeric(assigned_df['Slot'], errors='coerce')
        assigned_df['C'] = pd.to_numeric(assigned_df['Channel'], errors='coerce')
        
        print("First 10 rows:")
        print(assigned_df[['PID_TAG', 'N', 'S', 'C']].head(10).to_string())
        
        # Verify sort
        is_good = True
        for i in range(min(100, len(assigned_df)-1)):
            n_i, s_i, c_i = assigned_df['N'].iloc[i], assigned_df['S'].iloc[i], assigned_df['C'].iloc[i]
            n_next, s_next, c_next = assigned_df['N'].iloc[i+1], assigned_df['S'].iloc[i+1], assigned_df['C'].iloc[i+1]
            
            if pd.isna(n_i) or pd.isna(n_next):
                continue
            
            # Check order
            if (n_i, s_i, c_i) <= (n_next, s_next, c_next):
                continue
            else:
                print(f"Sort error at row {i}: ({n_i}, {s_i}, {c_i}) vs ({n_next}, {s_next}, {c_next})")
                is_good = False
                break
        
        if is_good:
            print("\nSUCCESS: Data is properly sorted by Node -> Slot -> Channel")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No output files found. Need to run the tool with input data first.")
