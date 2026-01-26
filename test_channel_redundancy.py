#!/usr/bin/env python3
"""Test the new channel-based redundancy logic"""

import pandas as pd
import glob
import os

# Remove old output file
output_files = glob.glob('Design Input Review_*.xlsx')
for f in output_files:
    try:
        os.remove(f)
        print(f"Removed old file: {f}")
    except:
        pass

print("\n" + "=" * 70)
print("TESTING NEW CHANNEL-BASED REDUNDANCY LOGIC")
print("=" * 70)

# Import and run the reviewer
exec(open('Design Input Review.py').read())

try:
    reviewer = DesignInputReview()
    output_file = reviewer.generate_output_file()
    
    if output_file and os.path.exists(output_file):
        print(f"\n✓ Output file created: {output_file}")
        
        assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
        
        print("\n[TEST 1] AI-R Redundant Signals - First 20 rows:")
        ai_r_signals = assigned_df[assigned_df['IO_type'].str.contains('AI-R', na=False)]
        
        if len(ai_r_signals) > 0:
            display_cols = ['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'Node', 'Slot', 'Channel', 'Redundancy_Flag']
            print(ai_r_signals[display_cols].head(20).to_string())
            
            print("\n[ANALYSIS]")
            print("Expected: Redundant signals use odd channels (1, 3, 5, 7...)")
            print("For each slot, channels should be: 1, 3, 5, 7, 9, 11, 13, 15 (for redundant)")
            
            # Verify redundancy_flag is 'Yes' for all
            redundant_yes = ai_r_signals[ai_r_signals['IO_REDUNDANCY'] == 'Y']
            redundant_flag_yes = redundant_yes[redundant_yes['Redundancy_Flag'] == 'Yes']
            print(f"\nAI-R with IO_REDUNDANCY='Y': {len(redundant_yes)}")
            print(f"AI-R with Redundancy_Flag='Yes': {len(redundant_flag_yes)}")
            if len(redundant_yes) == len(redundant_flag_yes):
                print("✓ All redundant AI-R signals have Redundancy_Flag='Yes'")
            else:
                print("✗ Redundancy_Flag mismatch!")
            
            # Check channel pattern
            print("\n[CHANNEL PATTERN CHECK]")
            slot_1_data = ai_r_signals[ai_r_signals['Slot'] == 1]
            if len(slot_1_data) > 0:
                channels = sorted(slot_1_data['Channel'].unique())
                print(f"Slot 1 channels used: {channels}")
                expected_odd = [1, 3, 5, 7, 9, 11, 13, 15]
                if channels == expected_odd[:len(channels)]:
                    print("✓ Channels are odd numbers as expected")
                else:
                    print("✗ Channel pattern incorrect")
        
        print("\n[TEST 2] DI-RL Redundant Signals - First 10 rows:")
        di_rl_signals = assigned_df[assigned_df['IO_type'].str.contains('DI-RL', na=False)]
        
        if len(di_rl_signals) > 0:
            print(f"Total DI-RL assigned: {len(di_rl_signals)}")
            print(di_rl_signals[display_cols].head(10).to_string())
            
            # Verify redundancy_flag is 'Yes' for all
            redundant_yes = di_rl_signals[di_rl_signals['IO_REDUNDANCY'] == 'Y']
            redundant_flag_yes = redundant_yes[redundant_yes['Redundancy_Flag'] == 'Yes']
            print(f"\nDI-RL with IO_REDUNDANCY='Y': {len(redundant_yes)}")
            print(f"DI-RL with Redundancy_Flag='Yes': {len(redundant_flag_yes)}")
            if len(redundant_yes) == len(redundant_flag_yes):
                print("✓ All redundant DI-RL signals have Redundancy_Flag='Yes'")
            else:
                print("✗ Redundancy_Flag mismatch!")
        
        print("\n[TEST 3] Sorting Verification (Node → Slot → Channel):")
        
        # Check sorting
        assigned_df['Node_num'] = pd.to_numeric(assigned_df['Node'], errors='coerce')
        assigned_df['Slot_num'] = pd.to_numeric(assigned_df['Slot'], errors='coerce')
        assigned_df['Channel_num'] = pd.to_numeric(assigned_df['Channel'], errors='coerce')
        
        is_sorted = True
        for i in range(min(30, len(assigned_df) - 1)):
            node_i = assigned_df['Node_num'].iloc[i]
            node_next = assigned_df['Node_num'].iloc[i + 1]
            slot_i = assigned_df['Slot_num'].iloc[i]
            slot_next = assigned_df['Slot_num'].iloc[i + 1]
            ch_i = assigned_df['Channel_num'].iloc[i]
            ch_next = assigned_df['Channel_num'].iloc[i + 1]
            
            if pd.isna(node_i) or pd.isna(node_next):
                continue
            
            if node_i < node_next:
                continue
            elif node_i == node_next:
                if slot_i < slot_next:
                    continue
                elif slot_i == slot_next:
                    if ch_i <= ch_next:
                        continue
                    else:
                        is_sorted = False
                        break
                else:
                    is_sorted = False
                    break
            else:
                is_sorted = False
                break
        
        if is_sorted:
            print("✓ Data is properly sorted by Node → Slot → Channel")
            print("\nFirst 20 rows (sorted):")
            print(assigned_df[['PID_TAG', 'Node_num', 'Slot_num', 'Channel_num']].head(20).to_string())
        else:
            print("✗ Sorting is not correct")
        
        print("\n[TEST 4] Capacity Analysis:")
        print(f"Total assigned: {len(assigned_df)}")
        unassigned_df = pd.read_excel(output_file, sheet_name='Unassigned')
        print(f"Total unassigned: {len(unassigned_df)}")
        
        # Show module utilization
        if 'Module_Name' in assigned_df.columns:
            print("\nModule usage (assigned signals):")
            print(assigned_df['Module_Name'].value_counts().to_string())
        
    else:
        print("✗ Output file not created")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
