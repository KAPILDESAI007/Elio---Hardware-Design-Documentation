#!/usr/bin/env python3
"""Debug why DI and DO spares are unassigned"""
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
    {'PID_TAG': 'SPARE84', 'signal_origin': 'Safety', 'IO_type': 'DI-RL', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
    {'PID_TAG': 'SPARE85', 'signal_origin': 'Safety', 'IO_type': 'DO', 'IO_REDUNDANCY': '', 'IS_Non_IS': 'NIS'},
]
spares_df = pd.DataFrame(new_spares)
reviewer.df_instruments = pd.concat([reviewer.df_instruments, spares_df], ignore_index=True)

# Extract
reviewer.extract_required_columns()
reviewer.df_assigned = reviewer.df_instruments.copy()  # Prepare assigned dataframe

# Check the extracted IO_type_base
print("=== EXTRACTED IO_TYPE_BASE FOR SPARES ===")
for idx, row in reviewer.df_instruments[reviewer.df_instruments['PID_TAG'].str.contains('SPARE7', case=False, na=False)].iterrows():
    print(f"{row['PID_TAG']:20s} | IO_type: {row['IO_type']:10s} | IO_type_base: {row['IO_type_base']}")

# Apply user inputs
reviewer.apply_user_inputs()
reviewer.sort_by_pid_tag()
reviewer.read_hardware_config()

# Check hardware config
print("\n=== HARDWARE DI/DO MODULES ===")
hardware_di = reviewer.df_hardware[reviewer.df_hardware['IO_Type'].str.contains('DI', case=False, na=False)]
hardware_do = reviewer.df_hardware[reviewer.df_hardware['IO_Type'].str.contains('DO', case=False, na=False)]
print(f"DI modules: {len(hardware_di)}")
print(f"DO modules: {len(hardware_do)}")

if len(hardware_di) > 0:
    print("\nSample DI modules:")
    print(hardware_di[['Module', 'IO_Type']].drop_duplicates().head())

if len(hardware_do) > 0:
    print("\nSample DO modules:")
    print(hardware_do[['Module', 'IO_Type']].drop_duplicates().head())

# Check module map that will be created
print("\n=== MODULE MAP CREATION ===")
module_map = {}
for _, row in reviewer.df_hardware.drop_duplicates(subset=['Module', 'IO_Type']).iterrows():
    io_type = str(row.get('IO_Type', '')).upper().strip()
    module_name = str(row.get('Module', '')).strip()
    if io_type and module_name:
        base_type = reviewer._extract_io_type_base(io_type)
        base_type_normalized = base_type.split('-')[0]
        if base_type_normalized not in module_map:
            module_map[base_type_normalized] = []
            print(f"Adding {base_type_normalized} -> {module_name}")

print(f"\nModule map keys: {list(module_map.keys())}")
print(f"Available module types: {list(module_map.keys())}")

# Check what signals would try to match DI
print("\n=== SIGNALS THAT WOULD MATCH DI ===")
di_signals = reviewer.df_assigned[reviewer.df_assigned['IO_type_base'] == 'DI']
print(f"DI type signals: {len(di_signals)}")
print("Sample DI signals:")
print(di_signals[['PID_TAG', 'IO_type_base', 'IS_Non_IS']].head(10))
