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

# Create instance and test with the actual input file WITH WIRED SPARES
print("Testing with wired spares (20% distribution)...")
review = DesignInputReview(wired_spares=20)  # 20% wired spares

# Manually set the instrument file to the actual test file
review.df_instruments = pd.read_excel("3291-36930B-J032-020 RevC_ESD.xls")
print(f"[DEBUG] Loaded {len(review.df_instruments)} instruments from ESD file")

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
assigned = review.df_assigned[review.df_assigned['Module_Instance'] != '']
print(f'\n========== ASSIGNMENT RESULTS ==========')
print(f'Total assigned: {len(assigned)}')

# Generate wired spares
spares = review.generate_wired_spares()

if len(spares) > 0:
    print(f'\n========== WIRED SPARES RESULTS ==========')
    print(f'Total wired spares: {len(spares)}')
    print(f'\nSpare sample (first 20):')
    print(spares[['PID_TAG', 'Module_Name', 'Controller_No', 'Node', 'Slot', 'Channel']].head(20).to_string())
    
    # Show distribution by module instance
    print(f'\nSpares per module instance:')
    for module_name in sorted(spares['Module_Name'].unique()):
        module_spares = spares[spares['Module_Name'] == module_name]
        instances = module_spares['Module_Instance'].value_counts().sort_index()
        print(f'  {module_name}: {len(module_spares)} total')
        for instance, count in instances.items():
            print(f'    {instance}: {count} spares')
else:
    print("No wired spares generated")
