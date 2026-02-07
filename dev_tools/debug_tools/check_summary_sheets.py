import pandas as pd
import openpyxl

# Check what's in the output file
print("Checking output file...")
wb = openpyxl.load_workbook('Design Input Review_2026-02-07.xlsx')
print(f"Sheet names: {wb.sheetnames}")

# Check if summary sheets were created but not written
df_assigned = pd.read_excel('Design Input Review_2026-02-07.xlsx', sheet_name='Assigned')
print(f"\nAssigned sheet has {len(df_assigned)} rows")

# Now let's manually call the generate methods to see what they return
from Design_Input_Review import DesignInputReview
import os

os.chdir(r'c:\Working\Others\Python\Cloud App Projects')
dir_obj = DesignInputReview(r'c:\Working\Others\Python\Cloud App Projects')

# Load some data first
print("\nLoadingtest data...")
if dir_obj.load_design_input_file('uploads/sample_design_input.xls'):
    print("Data loaded successfully")
    
    # Now try to generate summaries
    card_summary = dir_obj.generate_io_card_summary()
    print(f"\nIO Card Summary type: {type(card_summary)}")
    print(f"IO Card Summary empty: {card_summary.empty if hasattr(card_summary, 'empty') else 'N/A'}")
    print(f"IO Card Summary:\n{card_summary}")
    
    io_summary = dir_obj.generate_io_summary()
    print(f"\nIO Summary type: {type(io_summary)}")
    print(f"IO Summary empty: {io_summary.empty if hasattr(io_summary, 'empty') else 'N/A'}")
    print(f"IO Summary:\n{io_summary}")
else:
    print("Could not load test data")
