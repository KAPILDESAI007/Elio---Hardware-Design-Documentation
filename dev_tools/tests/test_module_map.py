#!/usr/bin/env python
"""
Test the module_map creation to see if DO/DI modules are being added correctly
"""

import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, r'c:\Working\Others\Python\Cloud App Projects')

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location("design_input_review", 
    r"c:\Working\Others\Python\Cloud App Projects\Design Input Review.py")
design_input_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design_input_review)
DesignInputReview = design_input_review.DesignInputReview

print("\n" + "="*100)
print("Testing module_map building for DO and DI modules")
print("="*100)

# Create a test reviewer
reviewer = DesignInputReview(
    system_type="ESD",
    controller_model="SCS60S",
    temperature_rating="Standard",
    is_types={},
    redundancy_types={}
)

# Read the constraints file
constraints_file = Path('templates/Yokogawa_SIS_Constraints_Model_v3.xlsx')
df_hardware = pd.read_excel(constraints_file, sheet_name='IO_Module_Catalog')

# Filter for FIO
df_fio = df_hardware[df_hardware['Family'] == 'FIO'].copy()

print(f"\nTotal FIO modules in catalog: {len(df_fio)}")
print(f"Unique IO_Types in FIO: {df_fio['IO_Type'].unique()}")
print(f"Unique Module names in FIO: {df_fio['Module'].unique()}")

# Now simulate what the code does
module_map = {}
for _, row in df_fio.iterrows():
    io_type = str(row.get('IO_Type', '')).strip()
    module_name = str(row.get('Module', '')).strip()
    
    base_type = design_input_review.DesignInputReview._extract_io_type_base(io_type)
    # Normalize
    base_type_normalized = base_type.split('-')[0]
    
    print(f"IO_Type={io_type:5} → base_type={base_type:3} → normalized={base_type_normalized:3} | Module={module_name}")
    
    if base_type_normalized not in module_map:
        module_map[base_type_normalized] = []
    
    module_map[base_type_normalized].append({'name': module_name})

print("\n" + "="*100)
print("Final module_map:")
print("="*100)
for io_type_base, modules in sorted(module_map.items()):
    unique_names = set([m['name'] for m in modules])
    print(f"{io_type_base}: {unique_names}")

print("\n" + "="*100)
print("Checking if DI and DO modules are accessible:")
print("="*100)
print(f"'DI' in module_map: {'DI' in module_map}")
print(f"'DO' in module_map: {'DO' in module_map}")
if 'DI' in module_map:
    print(f"DI modules: {[m['name'] for m in module_map['DI']]}")
if 'DO' in module_map:
    print(f"DO modules: {[m['name'] for m in module_map['DO']]}")

