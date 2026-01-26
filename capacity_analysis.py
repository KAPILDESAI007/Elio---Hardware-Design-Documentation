#!/usr/bin/env python3
"""Check module allocation and understand capacity"""

import pandas as pd
import glob

output_files = glob.glob('Design Input Review_*.xlsx')
output_file = sorted(output_files)[-1]

assigned_df = pd.read_excel(output_file, sheet_name='Assigned')

print("Columns in Assigned sheet:")
print(assigned_df.columns.tolist())

print("\n" + "=" * 70)
print("DI-RL MODULE ALLOCATION ANALYSIS")
print("=" * 70)

# Get DI-RL assigned signals
di_rl = assigned_df[assigned_df['IO_type'].str.contains('DI-RL', na=False)].copy()
print(f"\nTotal DI-RL Assigned: {len(di_rl)}")

# Group by Module_Name to see which modules are handling DI-RL
if 'Module_Name' in di_rl.columns:
    print("\nDI-RL by Module:")
    module_counts = di_rl['Module_Name'].value_counts()
    for module, count in module_counts.items():
        print(f"  {module}: {count} signals")

# Show Node/Slot allocation for DI-RL
print("\nDI-RL allocation by Node and Slot:")
di_rl_allocation = di_rl.groupby(['Node', 'Slot']).size().reset_index(name='count')
print(di_rl_allocation.to_string())

print("\n" + "=" * 70)
print("CAPACITY EXPLANATION")
print("=" * 70)

print("""
Why 494-HS-459A cannot be assigned:

1. REDUNDANCY REQUIREMENT:
   - All DI-RL signals have IO_REDUNDANCY='Y'
   - Redundant signals need 2 consecutive slots
   - Pattern: Slot 1 (signal), Slot 2 (reserved)
            Slot 3 (signal), Slot 4 (reserved)
            Slot 5 (signal), Slot 6 (reserved)

2. AVAILABLE CAPACITY:
   - Node-1: 6 slots total = 3 redundant pairs max
   - Node-2+: 8 slots total = 4 redundant pairs max
   
3. ACTUAL USAGE:
   - Only 53 DI-RL signals could be assigned
   - These fill up available 2-slot pairs
   - Remaining 171 DI-RL signals (including 494-HS-459A) have no slots available

4. SOLUTION OPTIONS:
   a) Add more nodes (increase Node-2, Node-3, etc.)
   b) Reduce redundancy requirement for some signals
   c) Use external IO cards
   d) Accept that only critical DI-RL signals will have redundancy
""")

# Calculate how many nodes would be needed
print("\n" + "=" * 70)
print("CALCULATION: Nodes needed for all DI-RL signals")
print("=" * 70)

total_di_rl = 224
redundant_pairs_per_node = 4  # Assuming Node-2+
nodes_needed = (total_di_rl + redundant_pairs_per_node - 1) // redundant_pairs_per_node
print(f"\nTotal DI-RL signals: {total_di_rl}")
print(f"Redundant pairs per Node-2+: {redundant_pairs_per_node}")
print(f"Minimum nodes needed: {nodes_needed} nodes")
print(f"Current assigned: 53 signals (= {53/4} = 13.25 pairs)")
print(f"Still need: {total_di_rl - 53} more signal assignments")
print(f"Additional pairs needed: {(total_di_rl - 53 + 3) // 4} more nodes")
