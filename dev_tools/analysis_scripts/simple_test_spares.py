#!/usr/bin/env python3
"""Quick test with a few DI spares"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import importlib.util
import pandas as pd

spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

# Create a very simple test - just a few DI/DO signals + spares
test_data = [
    {'PID_TAG': 'DI-001', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'DI-002', 'signal_origin': 'Safety', 'IO_type': 'DI', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'DO-001', 'signal_origin': 'Safety', 'IO_type': 'DO', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE74', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE85', 'signal_origin': 'Safety', 'IO_type': 'DO', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
]
test_df = pd.DataFrame(test_data)

reviewer = DesignInputReview()
reviewer.df_instruments = test_df

reviewer.extract_required_columns()
reviewer.apply_user_inputs()
reviewer.sort_by_pid_tag()
reviewer.read_hardware_config()
reviewer.read_mounting_rule()
reviewer.read_controller_limits()
reviewer.assign_modules()

assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
unassigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] == '']

print(f"Assigned: {len(assigned)}")
print(f"Unassigned: {len(unassigned)}")

if len(unassigned) > 0:
    print("\nUnassigned:")
    for idx, row in unassigned.iterrows():
        print(f"  {row['PID_TAG']:20s} | Type: {row['IO_type_base']}")

if len(assigned) > 0:
    print("\nAssigned:")
    for idx, row in assigned.iterrows():
        print(f"  {row['PID_TAG']:20s} | Module: {row['Module_Name']:15s} | Instance: {row['Module_Instance']:20s} | Channel: {row['Channel']}")
