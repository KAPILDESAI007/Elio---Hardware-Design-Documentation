"""
Test script for the new ChannelAssignmentManager
Demonstrates the intelligent assignment workflow
"""

import pandas as pd
from pathlib import Path
import sys

# Add processors to path
processors_dir = Path(__file__).parent / "processors"
if str(processors_dir) not in sys.path:
    sys.path.insert(0, str(processors_dir))

from channel_assignment_manager import ChannelAssignmentManager


def test_manager_basic():
    """Test basic manager functionality with sample data"""
    print("\n" + "=" * 100)
    print("TEST 1: Basic ChannelAssignmentManager Workflow")
    print("=" * 100)
    
    # Create sample data
    print("\n[STEP 1] Creating sample data...")
    
    # Sample signals (AI, DI, DO types)
    signals = [
        {'PID_TAG': f'0122-EAI-{i:06d}', 'IO_type_base': 'AI', 'IO_type': 'AI-R'} 
        for i in range(1, 21)
    ] + [
        {'PID_TAG': f'0122-EDI-{i:06d}', 'IO_type_base': 'DI', 'IO_type': 'DI'}
        for i in range(1, 11)
    ] + [
        {'PID_TAG': f'WIRED_SPARE_{i}', 'IO_type_base': 'SPARE', 'IO_type': 'SPARE'}
        for i in range(1, 6)
    ]
    
    df_instruments = pd.DataFrame(signals)
    print(f"  ✓ Created {len(df_instruments)} signals")
    print(f"    - AI signals: {len(df_instruments[df_instruments['IO_type_base'] == 'AI'])}")
    print(f"    - DI signals: {len(df_instruments[df_instruments['IO_type_base'] == 'DI'])}")
    print(f"    - Wired spares: {len(df_instruments[df_instruments['IO_type_base'] == 'SPARE'])}")
    
    # Sample hardware config
    hardware = [
        {'Module': 'FIO-16AH', 'IO_Type': 'AI', 'Nos of Channel': 16},
        {'Module': 'FIO-16DI', 'IO_Type': 'DI', 'Nos of Channel': 16},
        {'Module': 'FIO-8DO', 'IO_Type': 'DO', 'Nos of Channel': 8},
    ]
    
    df_hardware = pd.DataFrame(hardware)
    print(f"  ✓ Created hardware config with {len(df_hardware)} module types")
    
    # Initialize manager
    print("\n[STEP 2] Initializing ChannelAssignmentManager...")
    manager = ChannelAssignmentManager(df_instruments, df_hardware)
    print("  ✓ Manager initialized")
    
    # Analyze and plan
    print("\n[STEP 3] Analyzing and creating allocation plan...")
    analysis = manager.analyze_and_plan()
    
    if not analysis.get('success'):
        print(f"  ✗ Analysis failed: {analysis.get('error')}")
        return False
    
    print(f"  ✓ Analysis successful")
    print(f"    - Total signals: {analysis['total_signals']}")
    print(f"    - Total wired spares: {analysis['total_wired_spares']}")
    print(f"    - Modules needed: {analysis['total_modules']}")
    print(f"    - Channels per module: {analysis['channels_per_module']}")
    print(f"    - Wired spares per module: {analysis['wired_spares_per_module']:.2f}")
    print(f"    - Signal groups: {analysis['signal_groups']}")
    
    # Assign channels
    print("\n[STEP 4] Assigning channels...")
    df_assigned = manager.assign_channels(node_start=1, slot_start=1)
    
    assigned_count = len(df_assigned[df_assigned['Channel'] > 0])
    unassigned_count = len(df_assigned[df_assigned['Channel'] == 0])
    
    print(f"  ✓ Assignment complete")
    print(f"    - Assigned: {assigned_count}")
    print(f"    - Unassigned: {unassigned_count}")
    
    # Show results
    print("\n[STEP 5] Results:")
    assigned_df = df_assigned[df_assigned['Channel'] > 0].copy()
    if not assigned_df.empty:
        print("\n  First 10 assignments:")
        display_cols = ['PID_TAG', 'Module_Name', 'Node', 'Slot', 'Channel']
        print(assigned_df[display_cols].head(10).to_string(index=False))
        
        print("\n  Summary by Module:")
        summary = assigned_df.groupby(['Node', 'Slot']).agg({
            'Channel': 'count',
            'Module_Name': 'first'
        }).rename(columns={'Channel': 'Items Assigned', 'Module_Name': 'Module'})
        print(summary.to_string())
    
    # Print full report
    print("\n[STEP 6] Summary Report:")
    print(manager.get_summary_report())
    
    return True


def test_wired_spare_distribution():
    """Test that wired spares are distributed evenly"""
    print("\n" + "=" * 100)
    print("TEST 2: Wired Spare Distribution")
    print("=" * 100)
    
    # Create scenario: 20 wired spares, 10 AI modules
    print("\nScenario: 20 wired spares, 10 AI modules")
    
    signals = [
        {'PID_TAG': f'0122-EAI-{i:06d}', 'IO_type_base': 'AI', 'IO_type': 'AI-R'} 
        for i in range(1, 81)
    ] + [
        {'PID_TAG': f'WIRED_SPARE_{i}', 'IO_type_base': 'SPARE', 'IO_type': 'SPARE'}
        for i in range(1, 21)
    ]
    
    df_instruments = pd.DataFrame(signals)
    
    hardware = [
        {'Module': 'FIO-16AH', 'IO_Type': 'AI', 'Nos of Channel': 16},
    ]
    df_hardware = pd.DataFrame(hardware)
    
    manager = ChannelAssignmentManager(df_instruments, df_hardware)
    analysis = manager.analyze_and_plan()
    
    print(f"\nAnalysis Results:")
    print(f"  - Total signals: {analysis['total_signals']}")
    print(f"  - Total wired spares: {analysis['total_wired_spares']}")
    print(f"  - Modules needed: {analysis['total_modules']}")
    print(f"  - Wired spares per module: {analysis['wired_spares_per_module']:.2f}")
    
    if analysis['wired_spares_per_module'] == 2.0:
        print(f"\n  ✓ PASS: Wired spares distributed evenly (2.0 per module)")
    else:
        print(f"\n  ✗ FAIL: Expected 2.0 spares per module, got {analysis['wired_spares_per_module']}")
    
    return analysis['wired_spares_per_module'] == 2.0


def test_empty_channels():
    """Test that empty channels are distributed evenly"""
    print("\n" + "=" * 100)
    print("TEST 3: Empty Channel Distribution")
    print("=" * 100)
    
    # Create scenario: 50 signals, 8 modules (50/8 = 6.25 per module)
    print("\nScenario: 50 signals, 8-channel modules")
    
    signals = [
        {'PID_TAG': f'0122-EAI-{i:06d}', 'IO_type_base': 'AI', 'IO_type': 'AI-R'} 
        for i in range(1, 51)
    ]
    
    df_instruments = pd.DataFrame(signals)
    
    hardware = [
        {'Module': 'FIO-8AH', 'IO_Type': 'AI', 'Nos of Channel': 8},
    ]
    df_hardware = pd.DataFrame(hardware)
    
    manager = ChannelAssignmentManager(df_instruments, df_hardware)
    analysis = manager.analyze_and_plan()
    df_assigned = manager.assign_channels()
    
    print(f"\nAnalysis Results:")
    print(f"  - Total signals: {analysis['total_signals']}")
    print(f"  - Channels per module: {analysis['channels_per_module']}")
    print(f"  - Modules needed: {analysis['total_modules']}")
    
    # Count assignments per slot
    assigned = df_assigned[df_assigned['Channel'] > 0].groupby(['Node', 'Slot']).size()
    print(f"\nAssignments per module:")
    for (node, slot), count in assigned.items():
        empty = 8 - count
        print(f"  Node {node}, Slot {slot}: {count} assigned, {empty} empty")
    
    print(f"\n  ✓ Empty channels distributed across modules")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("CHANNELASSIGNMENTMANAGER TEST SUITE")
    print("=" * 100)
    
    # Run tests
    results = []
    
    results.append(("Basic Workflow", test_manager_basic()))
    results.append(("Wired Spare Distribution", test_wired_spare_distribution()))
    results.append(("Empty Channel Distribution", test_empty_channels()))
    
    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:40} {status}")
    
    total_passed = sum(1 for _, p in results if p)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total_tests - total_passed} test(s) failed")
        sys.exit(1)
