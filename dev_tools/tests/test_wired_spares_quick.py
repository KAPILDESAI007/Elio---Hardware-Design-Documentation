#!/usr/bin/env python3
"""Quick test of wired spare fixes with actual input file"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import using the dynamic loading method from app.py
import importlib.util
from pathlib import Path

design_review_path = Path(__file__).parent / "Design Input Review.py"
spec = importlib.util.spec_from_file_location("design_input_review", design_review_path)
design_review_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design_review_module)
DesignInputReview = design_review_module.DesignInputReview

print("\n" + "="*70)
print("TESTING WIRED SPARE FIXES")
print("="*70 + "\n")

try:
    # Use the most recent output file as input
    input_file = "Design Input Review_2026-02-07.xlsx"
    
    if not os.path.exists(input_file):
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)
    
    print(f"[INFO] Using test input file: {input_file}")
    
    # Create reviewer instance
    reviewer = DesignInputReview(
        system_type="ESD",
        controller_model="SCS0101",
        explosion_protection="Yes",
        temperature_rating="Standard",
        redundancy_types=["AI", "DI", "DO"],
        is_types=[],
        wired_spares=20.0,  # 20% wired spares
        io_types=["FIO"]
    )
    
    # Load input data
    print(f"\n[INFO] Reading input file...")
    import pandas as pd
    reviewer.df_instruments = pd.read_excel(input_file)
    print(f"[OK] Loaded {len(reviewer.df_instruments)} instruments")
    print(f"     Columns: {list(reviewer.df_instruments.columns[:10])}")
    
    # Run the processing steps
    print(f"\n[INFO] Executing review steps...")
    
    if not reviewer.extract_required_columns():
        raise Exception("Failed to extract required columns")
    print("  [OK] Extracted required columns")
    
    if not reviewer.apply_user_inputs():
        raise Exception("Failed to apply user inputs")
    print("  [OK] Applied user inputs")
    
    if not reviewer.sort_by_pid_tag():
        raise Exception("Failed to sort by PID_TAG")
    print("  [OK] Sorted by PID_TAG")
    
    if not reviewer.read_hardware_config():
        raise Exception("Failed to read hardware configuration")
    print("  [OK] Read hardware config")
    
    if not reviewer.read_mounting_rule():
        raise Exception("Failed to read mounting rule")
    print("  [OK] Read mounting rule")
    
    if not reviewer.read_controller_limits():
        raise Exception("Failed to read controller limits")
    print("  [OK] Read controller limits")
    
    if not reviewer.assign_modules():
        raise Exception("Failed to assign modules")
    print(f"  [OK] Assigned modules: {len(reviewer.df_assigned)} instruments assigned")
    
    # Check for wired spares in df_assigned
    ai_spares = reviewer.df_assigned[reviewer.df_assigned['PID_TAG'].astype(str).str.contains('AI_SPARE_', case=False, na=False)]
    di_spares = reviewer.df_assigned[reviewer.df_assigned['PID_TAG'].astype(str).str.contains('DI_SPARE_', case=False, na=False)]
    do_spares = reviewer.df_assigned[reviewer.df_assigned['PID_TAG'].astype(str).str.contains('DO_SPARE_', case=False, na=False)]
    
    print(f"\n[INFO] Wired spares in df_assigned (before regeneration):")
    print(f"  AI_SPARE: {len(ai_spares)}")
    print(f"  DI_SPARE: {len(di_spares)}")
    print(f"  DO_SPARE: {len(do_spares)}")
    print(f"  TOTAL: {len(ai_spares) + len(di_spares) + len(do_spares)}")
    
    if not reviewer.read_fio_config():
        raise Exception("Failed to read FIO configuration")
    print("  [OK] Read FIO config")
    
    if not reviewer.assign_nodes_and_controllers():
        raise Exception("Failed to assign nodes and controllers")
    print("  [OK] Assigned nodes and controllers")
    
    if not reviewer.identify_unassigned():
        raise Exception("Failed to identify unassigned")
    print("  [OK] Identified unassigned")
    
    # Generate output
    print(f"\n[INFO] Generating output file...")
    reviewer.generate_output_file()
    
    # Find the output file
    import glob
    output_files = glob.glob("Design Input Review_*.xlsx")
    if not output_files:
        raise Exception("No output file generated")
    
    output_file = sorted(output_files)[-1]  # Get the most recent one
    print(f"[OK] Output file created: {output_file}")
    
    # Verify output
    if os.path.exists(output_file):
        print(f"\n[INFO] Verifying output file...")
        xls = pd.ExcelFile(output_file)
        
        if 'Assigned' in xls.sheet_names:
            assigned = pd.read_excel(output_file, sheet_name='Assigned')
            
            # Look for regenerated spares (with SCS names and CH pattern)
            scs_spares = assigned[assigned['PID_TAG'].astype(str).str.contains(r'SCS.*_N\d+S\d+CH\d+', regex=True, na=False)]
            print(f"  Total rows in Assigned sheet: {len(assigned)}")
            print(f"  Regenerated wired spares (SCS pattern): {len(scs_spares)}")
            
            if len(scs_spares) > 0:
                print(f"\n[SUCCESS] Wired spares were regenerated to SCS format!")
                print(f"\nSample regenerated spares:")
                
                # Show distribution across nodes
                for node in sorted(scs_spares['Node'].unique())[:5]:
                    node_spares = scs_spares[scs_spares['Node'] == node]
                    slots = sorted(node_spares['Slot'].unique())
                    print(f"\n  Node {node}: {len(node_spares)} spares in {len(slots)} slots")
                    for idx, row in node_spares.head(3).iterrows():
                        print(f"    {row['PID_TAG']:30} -> N{int(row['Node']):02d}S{int(row['Slot']):02d}CH{int(row['Channel']):02d}")
                    if len(node_spares) > 3:
                        print(f"    ... and {len(node_spares) - 3} more")
                
                print(f"\n[DISTRIBUTION] Spares spread across {len(scs_spares['Node'].unique())} nodes")
                print(f"               {len(scs_spares['Slot'].unique())} slots")
                print(f"               {len(scs_spares['Module_Name'].unique())} different modules")
            else:
                print(f"[WARNING] No wired spares found in output!")
                print(f"\nFirst 20 PID_TAGs from output:")
                print(assigned['PID_TAG'].head(20).to_string())
        
        print(f"\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
    
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
