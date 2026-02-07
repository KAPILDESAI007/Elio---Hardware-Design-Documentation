#!/usr/bin/env python3
"""Analyze unassigned signals"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import importlib.util
import pandas as pd

# Load the module
spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

# Create instance and run assignment
reviewer = DesignInputReview()
test_file = 'Design Input Review_2026-01-31.xlsx'
reviewer.df_instruments = pd.read_excel(test_file)

# Run through the pipeline
if not reviewer.extract_required_columns():
    print("[FAILED] extract_required_columns")
    sys.exit(1)

if not reviewer.apply_user_inputs():
    print("[FAILED] apply_user_inputs")
    sys.exit(1)

if not reviewer.sort_by_pid_tag():
    print("[FAILED] sort_by_pid_tag")
    sys.exit(1)

if not reviewer.read_hardware_config():
    print("[FAILED] read_hardware_config")
    sys.exit(1)

if not reviewer.read_mounting_rule():
    print("[FAILED] read_mounting_rule")
    sys.exit(1)

if not reviewer.read_controller_limits():
    print("[FAILED] read_controller_limits")
    sys.exit(1)

if not reviewer.assign_modules():
    print("[FAILED] assign_modules")
    sys.exit(1)

# NOW - Check unassigned signals
unassigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] == '']
print(f"\n=== UNASSIGNED SIGNALS ({len(unassigned)}) ===\n")

# Check for spares
spares = unassigned[unassigned['PID_TAG'].str.contains('spare', case=False, na=False)]
print(f"Spare signals: {len(spares)}")
if len(spares) > 0:
    print("\nFirst 20 spares:")
    for idx, row in spares.head(20).iterrows():
        io_type = row.get('IO_type_base', '')
        is_type = row.get('IS_Non_IS', '')
        redundancy = row.get('IO_REDUNDANCY', '')
        print(f"  {row['PID_TAG']:30s} | Type: {io_type:8s} | IS/NIS: {is_type:5s} | R: {redundancy}")

# Check for DI-R, AI-R, etc.
print(f"\n=== SIGNAL TYPES IN UNASSIGNED ({len(unassigned)}) ===")
type_counts = unassigned['IO_type_base'].value_counts()
for io_type, count in type_counts.items():
    print(f"  {io_type}: {count}")

# Check for specific patterns
print(f"\n=== UNASSIGNED SIGNALS WITH 'R' (REDUNDANT) TYPES ===")
r_types = unassigned[unassigned['IO_type_base'].str.contains('R', case=False, na=False)]
print(f"Total with R types: {len(r_types)}")
if len(r_types) > 0:
    print("\nFirst 20:")
    for idx, row in r_types.head(20).iterrows():
        print(f"  {row['PID_TAG']:30s} | Type: {row.get('IO_type_base', ''):15s} | IS/NIS: {row.get('IS_Non_IS', ''):5s}")

# Show the available module types
print(f"\n=== AVAILABLE MODULES ===")
assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
modules = assigned['Module_Name'].unique()
for mod in sorted(modules):
    count = len(assigned[assigned['Module_Name'] == mod])
    print(f"  {mod}: {count} signals")
