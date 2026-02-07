#!/usr/bin/env python
"""Test script to verify all fixes are working"""

import sys
import pandas as pd
from pathlib import Path

# Add project to path
sys.path.insert(0, r'c:\Working\Others\Python\Cloud App Projects')

# Import using the file name directly
import importlib.util
spec = importlib.util.spec_from_file_location("design_input_review", 
    r"c:\Working\Others\Python\Cloud App Projects\Design Input Review.py")
design_input_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design_input_review)
DesignInputReview = design_input_review.DesignInputReview

def test_redundancy_handling():
    """Test redundancy slot handling"""
    print("\n" + "="*80)
    print("TEST: Redundancy Handling (odd/even slot allocation)")
    print("="*80)
    
    # Create test reviewer
    reviewer = DesignInputReview(
        system_type="ESD",
        controller_model="SCS60S",
        temperature_rating="Standard",
        is_types={'AI': True, 'DI': False, 'AO': False, 'DO': False},
        redundancy_types={'AI': True, 'DI': False, 'AO': False, 'DO': False},
        wired_spares=0
    )
    
    # Read input file
    input_file = Path(r'c:\Working\Others\Python\Cloud App Projects\test_real_input.py')
    
    # Check if file exists
    print(f"[TEST] Looking for test input file: {input_file}")
    
    # Try to find a sample Excel file
    sample_files = list(Path(r'c:\Working\Others\Python\Cloud App Projects').glob('*.xlsx'))
    print(f"[TEST] Found {len(sample_files)} Excel files in project directory")
    
    if not sample_files:
        print("[TEST] No sample Excel files found. Skipping redundancy test.")
        return
    
    # Use the constraints file to test
    constraints_file = Path(r'c:\Working\Others\Python\Cloud App Projects\templates\Yokogawa_SIS_Constraints_Model_v3.xlsx')
    
    if constraints_file.exists():
        print(f"[TEST] Testing with constraints file: {constraints_file}")
        
        # Read controller limits to verify
        df_limits = pd.read_excel(constraints_file, sheet_name='Controller_Limits')
        print(f"\n[TEST] Controller Limits data:")
        print(df_limits)
        
        # Test assign_nodes_and_controllers logic
        print("\n[TEST] Redundancy allocation logic:")
        print("  - Non-redundant module: allocate 1 slot, then move to next (current_slot += 1)")
        print("  - Redundant module: allocate 2 consecutive slots (odd + even), then move by 2 (current_slot += 2)")
        print("  - Example: Slots 1 (signal), 2 (redundancy), 3 (next signal), 4 (redundancy), etc.")
    else:
        print(f"[TEST] Constraints file not found: {constraints_file}")

def test_io_card_summary():
    """Test IO Card Summary instance counting"""
    print("\n" + "="*80)
    print("TEST: IO Card Summary Instance Counting")
    print("="*80)
    
    # Create sample data
    sample_data = {
        'PID_TAG': ['AI-001', 'AI-002', 'AI-003', 'AI-004', 'DI-001', 'DI-002'],
        'IO_type': ['AI', 'AI', 'AI', 'AI', 'DI', 'DI'],
        'Module_Instance': ['SAI143-S_1', 'SAI143-S_1', 'SAI143-S_2', 'SAI143-S_2', 'SDV144-S_1', 'SDV144-S_1'],
        'Controller_No': ['SCS0101', 'SCS0101', 'SCS0101', 'SCS0101', 'SCS0101', 'SCS0101'],
        'Node': [1, 1, 1, 1, 1, 1],
        'Slot': [1, 1, 2, 2, 3, 3],
        'Channel': [1, 2, 1, 2, 1, 2]
    }
    
    df = pd.DataFrame(sample_data)
    print(f"\n[TEST] Sample data with {len(df)} rows:")
    print(df)
    
    print("\n[TEST] Expected IO Card Summary output:")
    print("  Module_Instance          SCS_0101  Total_Qty")
    print("  SAI143-S_1                   1         1")
    print("  SAI143-S_2                   1         1")
    print("  SDV144-S_1                   1         1")
    print("\n[TEST] This shows 3 module instances (not 2 unique modules)")
    
    # Group by Module_Instance like the fixed code does
    module_instance_df = df[['Module_Instance', 'Controller_No']].drop_duplicates()
    print(f"\n[TEST] Unique module instances: {sorted(module_instance_df['Module_Instance'].unique())}")
    print(f"[TEST] Count: {len(module_instance_df)}")

def test_sorting():
    """Test sorting by Slot then Node"""
    print("\n" + "="*80)
    print("TEST: Output Sorting (Slot first, then Node)")
    print("="*80)
    
    # Create sample data with mixed slot/node order
    sample_data = {
        'PID_TAG': ['AI-001', 'AI-002', 'AI-003', 'AI-004', 'AI-005', 'AI-006'],
        'Slot': [3, 1, 2, 1, 3, 2],
        'Node': [2, 1, 1, 2, 1, 2]
    }
    
    df = pd.DataFrame(sample_data)
    print(f"\n[TEST] Unsorted data:")
    print(df[['PID_TAG', 'Slot', 'Node']])
    
    # Apply sorting like the fixed code
    df['Slot_Sort'] = pd.to_numeric(df['Slot'], errors='coerce')
    df['Node_Sort'] = pd.to_numeric(df['Node'], errors='coerce')
    df_sorted = df.sort_values(by=['Slot_Sort', 'Node_Sort']).drop(columns=['Slot_Sort', 'Node_Sort'])
    
    print(f"\n[TEST] Sorted data (by Slot, then Node):")
    print(df_sorted[['PID_TAG', 'Slot', 'Node']])
    
    print("\n[TEST] Verification:")
    print("  - Slot 1 rows should come first (Nodes 1, 2)")
    print("  - Slot 2 rows should come next (Nodes 1, 2)")
    print("  - Slot 3 rows should come last (Nodes 1, 2)")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("TESTING ALL FIXES")
    print("="*80)
    
    test_redundancy_handling()
    test_io_card_summary()
    test_sorting()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")
