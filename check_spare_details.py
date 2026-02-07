#!/usr/bin/env python3
"""Check why DI/DO are in module_map but spares are unassigned"""
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

# Now manually trace the assignment for DI signals
print("=== DI SIGNALS ===")
di_signals = reviewer.df_instruments[reviewer.df_instruments['IO_type_base'] == 'DI']
print(f"Total DI signals: {len(di_signals)}")
print(f"DI-IS signals: {len(di_signals[di_signals['IS_Non_IS'] == 'IS'])}")
print(f"DI-NIS signals: {len(di_signals[di_signals['IS_Non_IS'] == 'NIS'])}")

# Check spare signals
print("\n=== SPARE SIGNALS ===")
spares = reviewer.df_instruments[reviewer.df_instruments['PID_TAG'].str.contains('SPARE', na=False)]
print(f"Total spares: {len(spares)}")
for io_type, count in spares.groupby('IO_type_base').size().items():
    is_counts = spares[spares['IO_type_base'] == io_type].groupby('IS_Non_IS').size()
    print(f"  {io_type}: {count} total | IS={is_counts.get('IS', 0)}, NIS={is_counts.get('NIS', 0)}")

print("\n=== SPARE DETAILS ===")
for idx, row in spares.iterrows():
    print(f"{row['PID_TAG']:20s} | IO_type_base: {row['IO_type_base']:8s} | IS/NIS: {row['IS_Non_IS']:5s}")
