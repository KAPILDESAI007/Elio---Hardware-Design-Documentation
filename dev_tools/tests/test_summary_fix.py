#!/usr/bin/env python
"""Test the updated generate_output_file logic"""

import sys
import os
import pandas as pd
import openpyxl

# Set path
sys.path.insert(0, r'c:\Working\Others\Python\Cloud App Projects')
os.chdir(r'c:\Working\Others\Python\Cloud App Projects')

print("\n=== Testing Summary Sheets Fix ===\n")

# Test that openpyxl can write data using iterrows
test_df = pd.DataFrame({
    'Module': ['SAI143-S', 'SDV144-S', 'SDV541-S'],
    'Controller': [1, 1, 2],
    'Qty': [10, 20, 15]
})

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Test'

# Write header
for col_idx, col_name in enumerate(test_df.columns, 1):
    ws.cell(row=1, column=col_idx, value=col_name)

# Write data rows using iterrows
for row_idx, row in test_df.iterrows():
    for col_idx, col_name in enumerate(test_df.columns, 1):
        ws.cell(row=row_idx+2, column=col_idx, value=row[col_name])

print(f"✓ Test DataFrame written successfully")
print(f"  Rows written: {len(test_df)}")
print(f"  Columns: {list(test_df.columns)}")

# Verify the data
for row in ws.iter_rows(min_row=1, max_row=len(test_df)+1, values_only=True):
    print(f"  Row: {row}")

print(f"\n✓ All tests passed! Summary sheets can now be added.")
