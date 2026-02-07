#!/usr/bin/env python3
"""Check DI/DO module assignment"""
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

reviewer = DesignInputReview()
reviewer.df_instruments = pd.read_excel('Design Input Review_2026-01-31.xlsx')

# Add DI and DO spares
new_spares = [
    {'PID_TAG': 'SPARE74', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE85', 'signal_origin': 'Safety', 'IO_type': 'DO', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
]
spares_df = pd.DataFrame(new_spares)
reviewer.df_instruments = pd.concat([reviewer.df_instruments, spares_df], ignore_index=True)

reviewer.extract_required_columns()
reviewer.apply_user_inputs()
reviewer.sort_by_pid_tag()
reviewer.read_hardware_config()
reviewer.read_mounting_rule()
reviewer.read_controller_limits()
reviewer.assign_modules()

assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
di_assigned = assigned[assigned['Module_Name'].str.contains('SDV144', na=False)]
do_assigned = assigned[assigned['Module_Name'].str.contains('SDV541', na=False)]

print(f"DI signals assigned to SDV144-S: {len(di_assigned)}")
print(f"DO signals assigned to SDV541-S: {len(do_assigned)}")
print(f"\nDI module instances created:")
for instance in sorted(di_assigned['Module_Instance'].unique()):
    count = len(di_assigned[di_assigned['Module_Instance'] == instance])
    print(f"  {instance}: {count} signals")

print(f"\nDO module instances created:")
for instance in sorted(do_assigned['Module_Instance'].unique()):
    count = len(do_assigned[do_assigned['Module_Instance'] == instance])
    print(f"  {instance}: {count} signals")

unassigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] == '']
print(f"\nUnassigned: {len(unassigned)}")
if len(unassigned) > 0:
    print("Unassigned signals:")
    for idx, row in unassigned.iterrows():
        print(f"  {row['PID_TAG']:20s} | Type: {row['IO_type_base']:8s}")
