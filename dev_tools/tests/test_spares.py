#!/usr/bin/env python3
"""Test with spare signals added to verify assignment logic"""
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

print(f"Loaded {len(reviewer.df_instruments)} signals from {test_file}")

# Add some spare signals for testing
new_spares = [
    {'PID_TAG': 'SPARE74', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE75', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE84', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE85', 'signal_origin': 'Safety', 'IO_type': 'DO', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
]

# Add more spares to test distribution
for i in range(86, 102):  # 16 more spares
    io_type = 'AI-R' if i % 2 == 0 else 'DO-R'
    new_spares.append({
        'PID_TAG': f'SPARE{i}',
        'signal_origin': 'Safety',
        'IO_type': io_type,
        'IO_REDUNDANCY': 'R' if 'R' in io_type else '',
        'IS_Non_IS': 'NIS'
    })

spares_df = pd.DataFrame(new_spares)
reviewer.df_instruments = pd.concat([reviewer.df_instruments, spares_df], ignore_index=True)

print(f"Added {len(new_spares)} spare signals")
print(f"Total signals now: {len(reviewer.df_instruments)}\n")

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

# Check assignment results
assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
unassigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] == '']

print(f"\n=== ASSIGNMENT RESULTS ===")
print(f"Total signals: {len(reviewer.df_assigned)}")
print(f"Assigned: {len(assigned)}")
print(f"Unassigned: {len(unassigned)}")

if len(unassigned) > 0:
    print(f"\n=== UNASSIGNED SIGNALS ===")
    spare_unassigned = unassigned[unassigned['PID_TAG'].str.contains('SPARE', case=False, na=False)]
    print(f"Unassigned spares: {len(spare_unassigned)}")
    if len(spare_unassigned) > 0:
        print("\nFirst 20 unassigned spares:")
        for idx, row in spare_unassigned.head(20).iterrows():
            print(f"  {row['PID_TAG']:20s} | Type: {row.get('IO_type_base', ''):8s} | IS/NIS: {row.get('IS_Non_IS', ''):5s}")

# Check spare distribution in assigned
print(f"\n=== SPARE SIGNAL DISTRIBUTION ===")
assigned_spares = assigned[assigned['PID_TAG'].str.contains('SPARE', case=False, na=False)]
print(f"Assigned spares: {len(assigned_spares)}")
if len(assigned_spares) > 0:
    print("\nSpares by module instance:")
    for instance in sorted(assigned_spares['Module_Instance'].unique()):
        spares_in_instance = assigned_spares[assigned_spares['Module_Instance'] == instance]
        print(f"  {instance}: {len(spares_in_instance)} spares")

# Show DI and DO module distribution
print(f"\n=== MODULE DISTRIBUTION ===")
for module_type in ['DI', 'DO', 'AI']:
    module_assigned = assigned[assigned['Module_Name'].str.contains(module_type, case=False, na=False)]
    if len(module_assigned) > 0:
        module_instances = module_assigned['Module_Instance'].nunique()
        total_signals = len(module_assigned)
        spares = len(module_assigned[module_assigned['PID_TAG'].str.contains('SPARE', case=False, na=False)])
        print(f"\n{module_type} Modules:")
        print(f"  Instances: {module_instances}")
        print(f"  Total signals: {total_signals}")
        print(f"  Spares: {spares}")
