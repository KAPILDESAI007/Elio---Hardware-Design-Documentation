#!/usr/bin/env python3
"""Test Excel formatting and sorting"""

import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# Test that our fix works
print("Testing Excel formatting and sorting...")

# Import the DesignInputReview class
import sys
sys.path.insert(0, 'c:\\Working\\Others\\Python\\Cloud App Projects')

# Import using the proper module name (with underscore in file name becomes underscore in import)
exec(open('Design Input Review.py').read())
DesignInputReview = DesignInputReview  # Use the class from the exec'd module

# Create an instance and run the process
reviewer = DesignInputReview()

# Run the full process
print("\n[TEST] Running full process...")
output_file = reviewer.generate_output_file()
print(f"[TEST] Output file: {output_file}")

# Verify the file was created
if os.path.exists(output_file):
    print(f"[SUCCESS] File created: {output_file}")
    file_size = os.path.getsize(output_file)
    print(f"[INFO] File size: {file_size} bytes")
    
    # Check the workbook structure
    wb = load_workbook(output_file)
    print(f"\n[TEST] Worksheets in workbook: {wb.sheetnames}")
    
    # Test Assigned sheet
    if 'Assigned' in wb.sheetnames:
        ws_assigned = wb['Assigned']
        print(f"\n[TEST] Assigned sheet:")
        print(f"  - Freeze panes: {ws_assigned.freeze_panes}")
        print(f"  - Dimensions: {ws_assigned.dimensions}")
        print(f"  - Max row: {ws_assigned.max_row}, Max col: {ws_assigned.max_column}")
        
        # Check column widths
        print(f"  - Column widths:")
        for i in range(1, min(6, ws_assigned.max_column + 1)):
            col_letter = get_column_letter(i)
            width = ws_assigned.column_dimensions[col_letter].width
            header = ws_assigned.cell(1, i).value
            print(f"    - {col_letter} ({header}): {width}")
        
        # Check first few rows to verify sorting
        print(f"\n[TEST] First 10 data rows (checking sort by Slot, then Node):")
        assigned_df = pd.read_excel(output_file, sheet_name='Assigned')
        if 'Slot' in assigned_df.columns and 'Node' in assigned_df.columns:
            print(assigned_df[['PID_TAG', 'Slot', 'Node', 'Module_Name']].head(10).to_string())
            
            # Verify sorting
            if len(assigned_df) > 1:
                slots = pd.to_numeric(assigned_df['Slot'], errors='coerce')
                nodes = pd.to_numeric(assigned_df['Node'], errors='coerce')
                
                # Check if sorted
                is_sorted = True
                for i in range(len(assigned_df) - 1):
                    slot_i = slots.iloc[i]
                    slot_next = slots.iloc[i + 1]
                    node_i = nodes.iloc[i]
                    node_next = nodes.iloc[i + 1]
                    
                    if slot_i < slot_next:
                        continue  # Slot increased, good
                    elif slot_i == slot_next:
                        if node_i <= node_next:
                            continue  # Same slot, node increased or same, good
                        else:
                            is_sorted = False
                            print(f"  [ERROR] Row {i}: Slot {slot_i} Node {node_i} vs Row {i+1}: Slot {slot_next} Node {node_next}")
                            break
                    else:
                        is_sorted = False
                        print(f"  [ERROR] Row {i}: Slot {slot_i} vs Row {i+1}: Slot {slot_next}")
                        break
                
                if is_sorted:
                    print(f"[SUCCESS] Data is properly sorted by Slot, then Node")
                else:
                    print(f"[ERROR] Data sorting issue detected")
    
    # Test Unassigned sheet
    if 'Unassigned' in wb.sheetnames:
        ws_unassigned = wb['Unassigned']
        print(f"\n[TEST] Unassigned sheet:")
        print(f"  - Freeze panes: {ws_unassigned.freeze_panes}")
        print(f"  - Dimensions: {ws_unassigned.dimensions}")
        
        # Check column widths
        print(f"  - Sample column widths:")
        for i in range(1, min(4, ws_unassigned.max_column + 1)):
            col_letter = get_column_letter(i)
            width = ws_unassigned.column_dimensions[col_letter].width
            header = ws_unassigned.cell(1, i).value
            print(f"    - {col_letter} ({header}): {width}")
    
    # Test Summary sheet
    if 'Summary' in wb.sheetnames:
        ws_summary = wb['Summary']
        print(f"\n[TEST] Summary sheet:")
        print(f"  - Dimensions: {ws_summary.dimensions}")
        
        # Check column widths
        print(f"  - Sample column widths:")
        for i in range(1, min(3, ws_summary.max_column + 1)):
            col_letter = get_column_letter(i)
            width = ws_summary.column_dimensions[col_letter].width
            print(f"    - {col_letter}: {width}")
    
    print(f"\n[SUCCESS] Excel formatting test completed")
    
else:
    print(f"[ERROR] File was not created!")
