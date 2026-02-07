#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
import importlib.util
import pandas as pd

# Load the module with spaces in its name
spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

# Create instance and test
print("Testing assignment logic...")
reviewer = DesignInputReview()
reviewer.df_instruments = pd.read_excel('Design Input Review_2025-12-25.xlsx')

if not reviewer.extract_required_columns():
    print("Failed to extract required columns")
    sys.exit(1)

if not reviewer.apply_user_inputs():
    print("Failed to apply user inputs")
    sys.exit(1)

if not reviewer.sort_by_pid_tag():
    print("Failed to sort")
    sys.exit(1)

if not reviewer.read_hardware_config():
    print("Failed to read hardware")
    sys.exit(1)

if not reviewer.assign_modules_intelligent():
    print("Failed to assign modules intelligently")
    sys.exit(1)

if not reviewer.read_fio_config():
    print("Failed to read FIO")
    sys.exit(1)

if not reviewer.assign_nodes_and_controllers():
    print("Failed to assign nodes")
    sys.exit(1)

# Check results
assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
print(f'\n=== RESULTS ===')
print(f'Total assigned: {len(assigned)}')
print(f'Unique modules: {assigned["Module_Name"].nunique()}')
print(f'Modules: {sorted(assigned["Module_Name"].unique())}')
print(f'\nUnique nodes: {assigned["Node"].nunique()}')
print(f'\nSlots per node:')
for node in sorted(assigned['Node'].unique()):
    slots = sorted(assigned[assigned['Node'] == node]['Slot'].unique())
    print(f'  Node {node}: {len(slots)} slots -> {slots}')

print(f'\nTotal unassigned: {len(reviewer.df_assigned[reviewer.df_assigned["Module_Name"] == ""])}')
