#!/usr/bin/env python3
"""Test script to verify wired spare fixes"""

import sys
import os
import pandas as pd
import shutil

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the review class
try:
    from processors.channel_assignment_manager import ChannelAssignmentManager
    print("[OK] Module imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import: {e}")
    sys.exit(1)

# Run the test
print("\n" + "="*60)
print("TESTING WIRED SPARE FIXES")
print("="*60)

try:
    # Create instance
    mgr = ChannelAssignmentManager()
    print("[OK] ChannelAssignmentManager created")
    
    # Load sample data
    input_file = "Input Design_Input.xlsx"
    if not os.path.exists(input_file):
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)
    
    print(f"\n[INFO] Reading input file: {input_file}")
    mgr.read_input_file(input_file)
    print(f"[OK] Input file loaded: {len(mgr.df_instruments)} instruments")
    
    # Run assignment
    print("\n[INFO] Running channel assignment with wired spare fixes...")
    mgr.assign_modules()
    print(f"[OK] Assignment complete: {len(mgr.df_assigned)} assigned")
    
    # Check for wired spares in assigned dataframe
    ai_spares = mgr.df_assigned[mgr.df_assigned['PID_TAG'].str.contains('AI_SPARE_', na=False)]
    di_spares = mgr.df_assigned[mgr.df_assigned['PID_TAG'].str.contains('DI_SPARE_', na=False)]
    do_spares = mgr.df_assigned[mgr.df_assigned['PID_TAG'].str.contains('DO_SPARE_', na=False)]
    ao_spares = mgr.df_assigned[mgr.df_assigned['PID_TAG'].str.contains('AO_SPARE_', na=False)]
    
    print(f"\n[INFO] Wired spares in df_assigned:")
    print(f"  AI_SPARE: {len(ai_spares)}")
    print(f"  DI_SPARE: {len(di_spares)}")
    print(f"  DO_SPARE: {len(do_spares)}")
    print(f"  AO_SPARE: {len(ao_spares)}")
    print(f"  TOTAL: {len(ai_spares) + len(di_spares) + len(do_spares) + len(ao_spares)}")
    
    if len(ai_spares) > 0:
        print(f"\n[DEBUG] Sample AI_SPARE entries:")
        print(ai_spares[['PID_TAG', 'Node', 'Slot', 'Channel']].head(5))
    
    # Generate output
    output_file = "test_output.xlsx"
    print(f"\n[INFO] Generating output file: {output_file}")
    mgr.generate_output_file(output_file)
    print(f"[OK] Output file created")
    
    # Verify spares in output
    if os.path.exists(output_file):
        try:
            xls = pd.ExcelFile(output_file)
            if 'Assigned' in xls.sheet_names:
                assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
                
                # Check for wired spares with SCS pattern (regenerated)
                scs_spares = assigned_df[assigned_df['PID_TAG'].str.contains('SCS.*CH', regex=True, na=False)]
                print(f"\n[INFO] Wired spares in Excel output (SCS pattern):")
                print(f"  Count: {len(scs_spares)}")
                
                if len(scs_spares) > 0:
                    print(f"\n[SUCCESS] Sample regenerated wired spares:")
                    spare_samples = scs_spares[['PID_TAG', 'Node', 'Slot', 'Channel', 'Module_Name']].drop_duplicates('Node').head(10)
                    for idx, row in spare_samples.iterrows():
                        print(f"    {row['PID_TAG']:30} -> N{row['Node']:02d}S{row['Slot']:02d}CH{row['Channel']:02d} ({row['Module_Name']})")
                    
                    # Check distribution
                    nodes_with_spares = scs_spares['Node'].unique()
                    print(f"\n[INFO] Spares distributed across {len(nodes_with_spares)} nodes: {sorted(nodes_with_spares)}")
                    
                    # Check slots per node
                    for node in sorted(nodes_with_spares):
                        node_spares = scs_spares[scs_spares['Node'] == node]
                        slots = node_spares['Slot'].unique()
                        print(f"    Node {node}: {len(node_spares)} spares in {len(slots)} slots")
                else:
                    print(f"\n[WARNING] No wired spares found in Excel output!")
                    print(f"\nSample PID_TAGs from Excel:")
                    print(assigned_df['PID_TAG'].head(20).to_string())
        except Exception as e:
            print(f"[ERROR] Failed to read output Excel: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
