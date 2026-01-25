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

# Create instance and test with the actual input file
print("Testing assignment logic with ACTUAL INPUT FILE...")
review = DesignInputReview()

# Manually set the instrument file to the actual test file
review.df_instruments = pd.read_excel("3291-36930B-J032-020 RevC_ESD.xls")
print(f"[DEBUG] Loaded {len(review.df_instruments)} instruments from ESD file")
print(f"[DEBUG] Columns: {review.df_instruments.columns.tolist()}")

if not review.extract_required_columns():
    print("Failed to extract columns")
    sys.exit(1)

if not review.apply_user_inputs():
    print("Failed to apply user inputs")
    sys.exit(1)

if not review.sort_by_pid_tag():
    print("Failed to sort")
    sys.exit(1)

if not review.read_hardware_config():
    print("Failed to read hardware")
    sys.exit(1)

if not review.read_fio_config():
    print("Failed to read FIO")
    sys.exit(1)

if not review.assign_modules():
    print("Failed to assign modules")
    sys.exit(1)

if not review.assign_nodes_and_controllers():
    print("Failed to assign nodes")
    sys.exit(1)

# Check results
assigned = review.df_assigned[review.df_assigned['Module_Name'] != '']
print(f'\n========== ASSIGNMENT RESULTS ==========')
print(f'Total assigned: {len(assigned)}')
print(f'Unique modules: {assigned["Module_Name"].nunique()}')
print(f'Modules: {sorted(assigned["Module_Name"].unique())}')
print(f'\nUnique nodes: {assigned["Node"].nunique()}')
print(f'\nSlots per node:')
for node in sorted(assigned['Node'].unique()):
    slots = sorted(assigned[assigned['Node'] == node]['Slot'].unique())
    print(f'  Node {node}: {len(slots)} slots -> {slots}')

unassigned = review.df_assigned[review.df_assigned['Module_Name'] == '']
print(f'\nTotal UNASSIGNED: {len(unassigned)}')
if len(unassigned) > 0:
    print(f'Unassigned IO types: {unassigned["IO_type"].value_counts().to_dict()}')
