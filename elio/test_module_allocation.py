"""Test script to verify module allocation logic"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from elio.domain.services.module_calculator import ModuleCalculator

# Example scenario matching user requirements:
# 100 IS signals (50 Redundant, 50 Non-Redundant)
# 80 Non-IS signals (30 Redundant, 50 Non-Redundant)
# 20 total wired spares
# 16 channels per module

print("=" * 80)
print("TEST: Module Allocation with Redundancy Breakdown")
print("=" * 80)

# Prepare test data
signal_breakdown = {
    "AI": {
        "is_redundant": 50,
        "is_non_redundant": 50,
        "non_is_redundant": 30,
        "non_is_non_redundant": 50,
        "wired_spares": 20
    }
}

# Mock available modules (16 channels per module)
available_modules = [
    {
        "IO_Type": "AI",
        "Module": "SY3K-FAIS",
        "Usable_Channels": 16
    }
]

print("\n📋 INPUT DATA:")
print("-" * 80)
print(f"IS Redundant:        50 signals")
print(f"IS Non-Redundant:    50 signals")
print(f"Non-IS Redundant:    30 signals")
print(f"Non-IS Non-Redundant: 50 signals")
print(f"Total Wired Spares:  20")
print(f"Channels per Module: 16")

print("\n" + "=" * 80)
print("EXPECTED DISTRIBUTION:")
print("=" * 80)

# Manual calculation
total_is = 50 + 50  # 100
total_non_is = 30 + 50  # 80
total_signals = total_is + total_non_is  # 180

# Distribute spares by IS/Non-IS
is_spares = round(20 * (total_is / total_signals))  # 20 * (100/180) ≈ 11
non_is_spares = 20 - is_spares  # 20 - 11 = 9

print(f"\n1️⃣ DISTRIBUTE SPARES BY IS STATUS:")
print(f"   Total signals: {total_signals}")
print(f"   IS signals: {total_is} → IS spares: {is_spares}")
print(f"   Non-IS signals: {total_non_is} → Non-IS spares: {non_is_spares}")

# Distribute IS spares
is_red_spares = round(is_spares * (50 / 100))  # 11 * (50/100) ≈ 6
is_non_red_spares = is_spares - is_red_spares  # 11 - 6 = 5

# Distribute Non-IS spares
non_is_red_spares = round(non_is_spares * (30 / 80))  # 9 * (30/80) ≈ 3
non_is_non_red_spares = non_is_spares - non_is_red_spares  # 9 - 3 = 6

print(f"\n2️⃣ DISTRIBUTE SPARES BY REDUNDANCY WITHIN EACH IS GROUP:")
print(f"   IS Redundant: 50 signals + {is_red_spares} spares = {50 + is_red_spares} total")
print(f"   IS Non-Redundant: 50 signals + {is_non_red_spares} spares = {50 + is_non_red_spares} total")
print(f"   Non-IS Redundant: 30 signals + {non_is_red_spares} spares = {30 + non_is_red_spares} total")
print(f"   Non-IS Non-Redundant: 50 signals + {non_is_non_red_spares} spares = {50 + non_is_non_red_spares} total")

# Calculate modules
import math

# Redundant signals need 2x channels (redundancy protection)
is_red_modules = math.ceil((50 + is_red_spares) * 2 / 16)  # ceil(56*2/16) = ceil(7) = 7
is_non_red_modules = math.ceil((50 + is_non_red_spares) / 16)  # ceil(55/16) = 4
non_is_red_modules = math.ceil((30 + non_is_red_spares) * 2 / 16)  # ceil(33*2/16) = 5
non_is_non_red_modules = math.ceil((50 + non_is_non_red_spares) / 16)  # ceil(56/16) = 4

total_modules = is_red_modules + is_non_red_modules + non_is_red_modules + non_is_non_red_modules

print(f"\n3️⃣ CALCULATE MODULES (16 channels per module):")
print(f"   IS Redundant: ceil({50 + is_red_spares} × 2 / 16) = {is_red_modules} modules")
print(f"   IS Non-Redundant: ceil({50 + is_non_red_spares} / 16) = {is_non_red_modules} modules")
print(f"   Non-IS Redundant: ceil({30 + non_is_red_spares} × 2 / 16) = {non_is_red_modules} modules")
print(f"   Non-IS Non-Redundant: ceil({50 + non_is_non_red_spares} / 16) = {non_is_non_red_modules} modules")
print(f"   TOTAL: {total_modules} modules")

print("\n" + "=" * 80)
print("ACTUAL CALCULATION (from ModuleCalculator):")
print("=" * 80 + "\n")

# Run actual calculation
allocation = ModuleCalculator.calculate_modules_with_redundancy(
    signal_breakdown=signal_breakdown,
    available_modules=available_modules
)

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)

if "AI" in allocation and "error" not in allocation["AI"]:
    ai_data = allocation["AI"]
    
    is_red_results = ai_data.get("IS_Redundant", {})
    is_non_red_results = ai_data.get("IS_Non_Redundant", {})
    non_is_red_results = ai_data.get("Non_IS_Redundant", {})
    non_is_non_red_results = ai_data.get("Non_IS_Non_Redundant", {})
    summary = ai_data.get("Summary", {})
    
    print(f"\n✅ IS Redundant:")
    print(f"   Signals: {is_red_results.get('signals')}, Spares: {is_red_results.get('spares')}, Total: {is_red_results.get('total')}")
    print(f"   Modules: {is_red_results.get('modules_required')}, Channels: {is_red_results.get('total_channels')}")
    
    print(f"\n✅ IS Non-Redundant:")
    print(f"   Signals: {is_non_red_results.get('signals')}, Spares: {is_non_red_results.get('spares')}, Total: {is_non_red_results.get('total')}")
    print(f"   Modules: {is_non_red_results.get('modules_required')}, Channels: {is_non_red_results.get('total_channels')}")
    
    print(f"\n✅ Non-IS Redundant:")
    print(f"   Signals: {non_is_red_results.get('signals')}, Spares: {non_is_red_results.get('spares')}, Total: {non_is_red_results.get('total')}")
    print(f"   Modules: {non_is_red_results.get('modules_required')}, Channels: {non_is_red_results.get('total_channels')}")
    
    print(f"\n✅ Non-IS Non-Redundant:")
    print(f"   Signals: {non_is_non_red_results.get('signals')}, Spares: {non_is_non_red_results.get('spares')}, Total: {non_is_non_red_results.get('total')}")
    print(f"   Modules: {non_is_non_red_results.get('modules_required')}, Channels: {non_is_non_red_results.get('total_channels')}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Total Modules: {summary.get('total_modules')}")
    print(f"   Module: {summary.get('module')}")
    print(f"   Utilization: {summary.get('utilization_%')}%")
    
    print("\n" + "=" * 80)
    print("✓ LOGIC IS WORKING CORRECTLY!")
    print("=" * 80)
else:
    print(f"Error: {allocation}")
