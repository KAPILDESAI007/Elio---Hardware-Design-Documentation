#!/usr/bin/env python3
"""
Detailed comparison showing BEFORE and AFTER wired spare distribution.
This demonstrates the improvement in even distribution.
"""
import pandas as pd

print("="*90)
print("WIRED SPARE DISTRIBUTION: BEFORE vs AFTER COMPARISON")
print("="*90)

print("\n" + "SCENARIO: 10 modules × 2 instances each = 20 total instances")
print("          160 assigned channels × 20% = 32 wired spares to distribute")
print("          Hardware capacity per instance: 16 channels")

print("\n" + "="*90)
print("BEFORE FIX (OLD ALGORITHM): Sequential Fill-Up")
print("="*90)
print("\nAlgorithm: Fill each instance to max capacity before moving to next")
print("\nDistribution:")

before_distribution = [
    ("AI_Module_1_1", 8),   # Filled to 16: 8 assigned + 8 spares
    ("AI_Module_1_2", 8),   # Filled to 16: 8 assigned + 8 spares
    ("AI_Module_2_1", 8),   # Filled to 16: 8 assigned + 8 spares
    ("AI_Module_2_2", 8),   # Filled to 16: 8 assigned + 8 spares
    ("AI_Module_3_1", 0),   # NO SPARES - already full with 8 assigned
    ("AI_Module_3_2", 0),   # NO SPARES
    ("AI_Module_4_1", 0),   # NO SPARES
    ("AI_Module_4_2", 0),   # NO SPARES
    ("AI_Module_5_1", 0),   # NO SPARES
    ("AI_Module_5_2", 0),   # NO SPARES
    ("AI_Module_6_1", 0),   # NO SPARES
    ("AI_Module_6_2", 0),   # NO SPARES
    ("AI_Module_7_1", 0),   # NO SPARES
    ("AI_Module_7_2", 0),   # NO SPARES
    ("AI_Module_8_1", 0),   # NO SPARES
    ("AI_Module_8_2", 0),   # NO SPARES
    ("AI_Module_9_1", 0),   # NO SPARES
    ("AI_Module_9_2", 0),   # NO SPARES
    ("AI_Module_10_1", 0),  # NO SPARES
    ("AI_Module_10_2", 0),  # NO SPARES
]

total_before = sum([spares for _, spares in before_distribution])
print(f"\nModule Instance          | Assigned | Wired Spares | Total | Blank Channels")
print("-" * 75)
for instance, spares in before_distribution:
    assigned = 8
    total = assigned + spares
    blank = 16 - total
    status = "✓ FULL" if spares == 8 else "✗ EMPTY" if spares == 0 else ""
    print(f"{instance:24} |    {assigned:2}    |     {spares:2}      | {total:2}   |      {blank:2}         {status}")

print("-" * 75)
print(f"{'TOTAL SPARES':24} |          |            | {total_before:3} |")

print("\n" + "⚠ PROBLEMS:")
print("  • Only 4 out of 20 instances (20%) have wired spares")
print("  • 16 instances (80%) have ZERO backup capacity")
print("  • User sees only 3 wired spares: SCS0101_N1S3CH14, CH15, CH16")
print("  • 12 modules have no redundancy/spares at all")

print("\n" + "="*90)
print("AFTER FIX (NEW ALGORITHM): Even Distribution")
print("="*90)
print("\nAlgorithm: Distribute spares evenly → 32 ÷ 20 = 1 base + 12 remainder")
print("          → First 12 instances get 2 spares, Last 8 instances get 1 spare")

after_distribution = [
    ("AI_Module_1_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_1_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_2_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_2_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_3_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_3_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_4_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_4_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_5_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_5_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_6_1", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_6_2", 2),   # 8 assigned + 2 spares = 10 used, 6 blank
    ("AI_Module_7_1", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_7_2", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_8_1", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_8_2", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_9_1", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_9_2", 1),   # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_10_1", 1),  # 8 assigned + 1 spare  = 9 used, 7 blank
    ("AI_Module_10_2", 1),  # 8 assigned + 1 spare  = 9 used, 7 blank
]

total_after = sum([spares for _, spares in after_distribution])
print(f"\nModule Instance          | Assigned | Wired Spares | Total | Blank Channels")
print("-" * 75)
for instance, spares in after_distribution:
    assigned = 8
    total = assigned + spares
    blank = 16 - total
    status = "✓ 2 SPARES" if spares == 2 else "✓ 1 SPARE" if spares == 1 else ""
    print(f"{instance:24} |    {assigned:2}    |     {spares:2}      | {total:2}   |      {blank:2}         {status}")

print("-" * 75)
print(f"{'TOTAL SPARES':24} |          |            | {total_after:3} |")

print("\n" + "✓ BENEFITS:")
print("  • ALL 20 instances (100%) have wired spares")
print("  • Every module instance has backup capacity")
print("  • Even distribution: min=1, max=2 spares per instance")
print("  • Blank channels evenly distributed: 6-7 per instance (instead of 10 in one)")
print("  • Every module gets wired spares, not just the first few")
print("  • Better redundancy and fault tolerance")

print("\n" + "="*90)
print("SUMMARY STATISTICS")
print("="*90)

before_with_spares = len([s for _, s in before_distribution if s > 0])
after_with_spares = len([s for _, s in after_distribution if s > 0])

before_min = min([s for _, s in before_distribution if s > 0]) if before_with_spares > 0 else 0
before_max = max([s for _, s in before_distribution if s > 0]) if before_with_spares > 0 else 0
after_min = min([s for _, s in after_distribution])
after_max = max([s for _, s in after_distribution])

print(f"\n{'Metric':40} | BEFORE | AFTER  | Improvement")
print("-" * 60)
print(f"{'Instances with spares':40} |  {before_with_spares:2}/20  |  {after_with_spares:2}/20  | {after_with_spares-before_with_spares:+3} instances")
print(f"{'Percentage of instances':40} |   {100*before_with_spares//20:2}%   |   {100*after_with_spares//20:2}%   | {100*(after_with_spares-before_with_spares)//20:+3}%")
print(f"{'Min spares per instance':40} |   {before_min:2}    |   {after_min:2}    | {after_min-before_min:+3}")
print(f"{'Max spares per instance':40} |   {before_max:2}    |   {after_max:2}    | {after_max-before_max:+3}")
print(f"{'Variance (max - min)':40} |   {before_max-before_min if before_with_spares > 0 else 'N/A':>2}    |   {after_max-after_min:2}    | Better")

print("\n" + "="*90)
print("REAL-WORLD IMPACT FOR YOUR CASE")
print("="*90)
print("""
Before: Only 3 wired spares visible in Node-1, Slot-3
        → SCS0101_N1S3CH14, SCS0101_N1S3CH15, SCS0101_N1S3CH16
        → Other slots had NO spares

After: Wired spares distributed evenly across ALL module instances
       → Each module instance gets proportional spares
       → Better system redundancy and reliability
       → No "starved" modules with zero spares
""")

print("="*90)
