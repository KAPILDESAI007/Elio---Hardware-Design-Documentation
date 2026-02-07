#!/usr/bin/env python3
"""
Test script to demonstrate even distribution of wired spares across module instances.
This creates synthetic test data to verify the distribution algorithm.
"""
import pandas as pd
import importlib.util

# Load the module with spaces in its name
spec = importlib.util.spec_from_file_location("design_input_review", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

print("="*80)
print("TESTING EVEN DISTRIBUTION OF WIRED SPARES - SYNTHETIC DATA")
print("="*80)

# Create a DesignInputReview instance with 20% wired spares
review = DesignInputReview(wired_spares=20)

# Create synthetic assigned data with 10 AI modules (2 instances each = 20 module instances)
# Each instance has 8 channels (80 total channels, 20 wired spares = 2 per instance)
assigned_data = []

# Create 10 module types with 2 instances each
for module_idx in range(10):  # 10 different module types
    module_name = f"AI_Module_{module_idx + 1}"
    
    for instance_idx in range(2):  # 2 instances per module type
        module_instance = f"{module_name}_{instance_idx + 1}"
        
        # Each instance gets 8 assigned channels (total 16 in the module, leaving 8 for spares)
        for channel in range(1, 9):
            assigned_data.append({
                'PID_TAG': f"TAG_M{module_idx + 1}_I{instance_idx + 1}_CH{channel}",
                'signal_origin': 'INPUT',
                'IO_type': 'AI',
                'IO_REDUNDANCY': '',
                'IS_Non_IS': 'NIS',
                'IO_type_base': 'AI',
                'Module_Name': module_name,
                'Module_Instance': module_instance,
                'Channel': channel,
                'Node': 1,
                'Slot': module_idx + 1,
                'Controller_No': 'SCS0101',
                'sort_prefix': '',
                'sort_type': '',
                'sort_base_num': 0,
                'sort_suffix': '',
                'sort_redundancy': ''
            })

review.df_assigned = pd.DataFrame(assigned_data)

# Create hardware config
review.df_hardware = pd.DataFrame([
    {'Module Name': f'AI_Module_{i+1}', 'Nos of Channel': 16}
    for i in range(10)
])

print(f"\nSetup:")
print(f"  - {len(review.df_assigned)} assigned channels")
print(f"  - {review.df_assigned['Module_Name'].nunique()} module types")
print(f"  - {review.df_assigned['Module_Instance'].nunique()} total module instances")
print(f"  - Wired spares: 20%")

# Generate wired spares
print("\n" + "="*80)
print("GENERATING WIRED SPARES WITH EVEN DISTRIBUTION")
print("="*80)

spares = review.generate_wired_spares()

if len(spares) == 0:
    print("ERROR: No wired spares generated!")
    exit(1)

print(f"\nGenerated: {len(spares)} wired spares")

# Analyze distribution by module name
print("\n" + "="*80)
print("DISTRIBUTION ANALYSIS")
print("="*80)

for module_name in sorted(spares['Module_Name'].unique()):
    module_spares = spares[spares['Module_Name'] == module_name]
    print(f"\n{module_name}:")
    print(f"  Total spares: {len(module_spares)}")
    
    # Show distribution per instance
    instance_distribution = {}
    for instance in sorted(module_spares['Module_Instance'].unique()):
        instance_spares = module_spares[module_spares['Module_Instance'] == instance]
        instance_distribution[instance] = len(instance_spares)
        channels = sorted(instance_spares['Channel'].tolist())
        print(f"    {instance}: {len(instance_spares)} spares on channels {channels}")
    
    # Check evenness
    counts = list(instance_distribution.values())
    if len(counts) > 0:
        min_count = min(counts)
        max_count = max(counts)
        diff = max_count - min_count
        
        if diff <= 1:
            print(f"  ✓ EVEN: min={min_count}, max={max_count} (difference=0)")
        else:
            print(f"  ⚠ UNEVEN: min={min_count}, max={max_count} (difference={diff})")

# Overall summary
print("\n" + "="*80)
print("OVERALL SUMMARY")
print("="*80)

total_instances = spares['Module_Instance'].nunique()
total_spares = len(spares)
avg_spares_per_instance = total_spares / total_instances

print(f"Total module instances: {total_instances}")
print(f"Total wired spares: {total_spares}")
print(f"Average spares per instance: {avg_spares_per_instance:.2f}")

# Check distribution across all instances
instance_counts = spares['Module_Instance'].value_counts()
min_spares_per_instance = instance_counts.min()
max_spares_per_instance = instance_counts.max()
variance = max_spares_per_instance - min_spares_per_instance

print(f"\nAcross all instances:")
print(f"  Min spares per instance: {min_spares_per_instance}")
print(f"  Max spares per instance: {max_spares_per_instance}")
print(f"  Variance: {variance}")

if variance <= 1:
    print("\n✓ SUCCESS: Wired spares are evenly distributed!")
else:
    print(f"\n⚠ WARNING: Distribution has variance of {variance}")

print("\n" + "="*80)
