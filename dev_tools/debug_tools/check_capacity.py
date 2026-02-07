#!/usr/bin/env python3
"""Check module capacity for DI and DO"""
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

# Create instance
reviewer = DesignInputReview()
test_file = 'Design Input Review_2026-01-31.xlsx'
reviewer.df_instruments = pd.read_excel(test_file)

# Add test spares
new_spares = [
    {'PID_TAG': 'SPARE74', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE75', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
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

# Check how many DI and DO signals need assignment
di_signals = reviewer.df_instruments[reviewer.df_instruments['IO_type_base'] == 'DI']
do_signals = reviewer.df_instruments[reviewer.df_instruments['IO_type_base'] == 'DO']

print(f"=== DI/DO SIGNAL COUNTS ===")
print(f"DI signals (all types): {len(di_signals)}")
print(f"DO signals (all types): {len(do_signals)}")

# Hardware capacity
print(f"\n=== HARDWARE CAPACITY ===")
print(f"SDV144-S (DI): 1 module x 16 channels = 16 channels")
print(f"SDV541-S (DO): 1 module x 16 channels = 16 channels")

# But we also use these modules for AI
di_hardware = reviewer.df_hardware[reviewer.df_hardware['Module'].str.contains('144', na=False)]
do_hardware = reviewer.df_hardware[reviewer.df_hardware['Module'].str.contains('541', na=False)]

print(f"\n=== ACTUAL HARDWARE CONFIG ===")
print(f"DI module count: {len(di_hardware)}")
print(f"DO module count: {len(do_hardware)}")

if len(di_hardware) > 0:
    print("\nDI hardware:")
    print(di_hardware[['Module', 'IO_Type']].drop_duplicates())

if len(do_hardware) > 0:
    print("\nDO hardware:")
    print(do_hardware[['Module', 'IO_Type']].drop_duplicates())

print(f"\n=== THE PROBLEM ===")
print(f"Currently SDV144-S is being used for BOTH DI AND AI signals!")
print(f"Currently SDV541-S is being used for both DO AND AI signals!")
print(f"This is causing capacity issues")
