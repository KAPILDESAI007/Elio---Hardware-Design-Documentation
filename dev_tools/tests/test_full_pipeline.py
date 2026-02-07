#!/usr/bin/env python3
"""Test the full pipeline with the duplicate fix"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import importlib.util
import pandas as pd
from pathlib import Path

# Load the module
spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

# Create instance
print("=" * 60)
print("FULL PIPELINE TEST - Duplicate Prevention Fix")
print("=" * 60)

reviewer = DesignInputReview()

# Load test file
test_file = 'Design Input Review_2026-01-31.xlsx'
print(f"\n1. Loading {test_file}...")
try:
    reviewer.df_instruments = pd.read_excel(test_file)
    print(f"   [OK] Loaded {len(reviewer.df_instruments)} instruments")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Extract columns
print(f"\n2. Extracting required columns...")
try:
    if not reviewer.extract_required_columns():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Extracted columns")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Apply user inputs  
print(f"\n3. Applying user inputs...")
try:
    if not reviewer.apply_user_inputs():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Applied inputs")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Sort
print(f"\n4. Sorting by PID tag...")
try:
    if not reviewer.sort_by_pid_tag():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Sorted")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Hardware
print(f"\n5. Reading hardware config...")
try:
    if not reviewer.read_hardware_config():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Read hardware")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Mounting rule
print(f"\n6. Reading mounting rule...")
try:
    if not reviewer.read_mounting_rule():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Read mounting rule")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Controller limits
print(f"\n7. Reading controller limits...")
try:
    if not reviewer.read_controller_limits():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Read controller limits")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# ASSIGN MODULES - The key test
print(f"\n8. Assigning modules (WITH DUPLICATE PREVENTION)...")
try:
    if not reviewer.assign_modules():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Assigned modules")
except Exception as e:
    print(f"   [FAILED] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Read FIO
print(f"\n9. Reading FIO configuration...")
try:
    if not reviewer.read_fio_config():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Read FIO config")
except Exception as e:
    print(f"   [FAILED] {e}")
    sys.exit(1)

# Assign nodes
print(f"\n10. Assigning nodes and controllers...")
try:
    if not reviewer.assign_nodes_and_controllers():
        print("   [FAILED]")
        sys.exit(1)
    print(f"   [OK] Assigned nodes and controllers")
except Exception as e:
    print(f"   [FAILED] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Generate output
print(f"\n11. Generating output file...")
try:
    output_file = reviewer.generate_output_file()
    if output_file:
        print(f"   [OK] Generated: {output_file}")
    else:
        print(f"   [FAILED] generate_output_file returned None")
        sys.exit(1)
except Exception as e:
    print(f"   [FAILED] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check if file exists
import os
if os.path.exists(output_file):
    file_size = os.path.getsize(output_file)
    print(f"   [OK] File exists: {file_size} bytes")
else:
    print(f"   [FAILED] File not found")
    sys.exit(1)

# Final validation
print(f"\n" + "=" * 60)
print("VALIDATION RESULTS")
print("=" * 60)

assigned = reviewer.df_assigned[reviewer.df_assigned['Module_Name'] != '']
print(f"\nAssignment Summary:")
print(f"  Total instruments: {len(reviewer.df_assigned)}")
print(f"  Assigned: {len(assigned)}")
print(f"  Unassigned: {len(reviewer.df_assigned) - len(assigned)}")

# Check for duplicates - CRITICAL
duplicates = assigned.groupby(['Module_Instance', 'Channel']).size()
duplicate_count = (duplicates > 1).sum()
print(f"\nDuplicate Check (CRITICAL):")
if duplicate_count == 0:
    print(f"  [OK] NO DUPLICATES - Each channel in each module has only 1 signal")
else:
    print(f"  [ERROR] {duplicate_count} duplicate assignments found!")

# Channel distribution
print(f"\nModule Instances Created: {assigned['Module_Instance'].nunique()}")
modules = sorted(assigned['Module_Name'].unique())
print(f"Unique Modules: {len(modules)}")
for mod in modules[:5]:
    count = len(assigned[assigned['Module_Name'] == mod])
    print(f"  - {mod}: {count} signals")
if len(modules) > 5:
    print(f"  ... and {len(modules) - 5} more")

print(f"\n" + "=" * 60)
print("[SUCCESS] FULL PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 60)
