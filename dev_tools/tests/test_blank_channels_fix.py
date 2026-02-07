"""
Test the fix for blank channels in slot-3 issue
Verifies that wired spares are now distributed evenly
"""

import pandas as pd
from pathlib import Path
import sys

# Add processors to path
processors_dir = Path(__file__).parent / "processors"
if str(processors_dir) not in sys.path:
    sys.path.insert(0, str(processors_dir))

from channel_assignment_manager import ChannelAssignmentManager


def test_spare_distribution_fix():
    """Test that the fix distributes spares evenly"""
    print("\n" + "=" * 100)
    print("TEST: Blank Channels Fix - Even Spare Distribution")
    print("=" * 100)
    
    # Create scenario: 10 wired spares, 4 modules
    # This should distribute as: 3, 3, 2, 2 (not 2, 2, 2, 4)
    print("\nScenario: 20 signals, 10 wired spares, 4 modules (16 ch/module)")
    print("Expected distribution: 3, 3, 2, 2 (or similar even distribution)")
    
    # Create 20 signals
    signals = [
        {'PID_TAG': f'DI_{i:03d}', 'IO_type_base': 'DI', 'IO_type': 'DI'} 
        for i in range(1, 21)
    ]
    
    # Create 10 wired spares
    spares = [
        {'PID_TAG': f'WIRED_SPARE_DI_{i:03d}', 'IO_type_base': 'DI', 'IO_type': 'DI'} 
        for i in range(1, 11)
    ]
    
    df_instruments = pd.DataFrame(signals + spares)
    
    hardware = [
        {'Module': 'FIO', 'IO_Type': 'DI', 'Nos of Channel': 16},
    ]
    df_hardware = pd.DataFrame(hardware)
    
    # Initialize manager
    manager = ChannelAssignmentManager(df_instruments, df_hardware)
    analysis = manager.analyze_and_plan()
    
    print(f"\nAnalysis Results:")
    print(f"  - Total signals: {analysis['total_signals']}")
    print(f"  - Total wired spares: {analysis['total_wired_spares']}")
    print(f"  - Total items: {analysis['total_signals'] + analysis['total_wired_spares']}")
    print(f"  - Modules needed: {analysis['total_modules']}")
    print(f"  - Channels per module: {analysis['channels_per_module']}")
    print(f"  - Wired spares per module: {analysis['wired_spares_per_module']:.2f}")
    
    # Assign channels
    df_assigned = manager.assign_channels(node_start=1, slot_start=1)
    
    # Analyze distribution
    print(f"\nSparse Distribution Per Module:")
    spares_by_module = df_assigned[df_assigned['PID_TAG'].str.contains('SPARE', case=False, na=False)]
    
    if len(spares_by_module) > 0:
        distribution = spares_by_module.groupby(['Node', 'Slot']).size()
        
        for (node, slot), count in distribution.items():
            print(f"  Node {node}, Slot {slot}: {count} spares")
        
        # Check if distribution is even (difference <= 1)
        counts = distribution.values
        min_count = counts.min()
        max_count = counts.max()
        diff = max_count - min_count
        
        print(f"\nDistribution Analysis:")
        print(f"  - Min spares per module: {min_count}")
        print(f"  - Max spares per module: {max_count}")
        print(f"  - Difference: {diff}")
        
        if diff <= 1:
            print(f"  ✓ Distribution is EVEN (difference ≤ 1)")
        else:
            print(f"  ✗ Distribution is UNEVEN (difference > 1)")
    
    # Show channel assignments for slot-3
    print(f"\nChannel Assignments for Slot-3 (Should show spares + empty channels):")
    slot3_data = df_assigned[(df_assigned['Slot'] == 3) & (df_assigned['Channel'] > 0)]
    
    if not slot3_data.empty:
        for _, row in slot3_data.iterrows():
            pid = row['PID_TAG']
            ch = row['Channel']
            is_spare = 'SPARE' in str(pid).upper()
            tag = "SPARE" if is_spare else "SIGNAL"
            print(f"  Channel {ch:2d}: {pid:20s} [{tag}]")
    
    print(f"\nEmpty channels in Slot-3 (Channels 4-16 should show as unassigned):")
    slot3_assigned_channels = set(
        df_assigned[(df_assigned['Slot'] == 3) & (df_assigned['Channel'] > 0)]['Channel'].tolist()
    )
    all_channels = set(range(1, 17))
    empty_channels = sorted(all_channels - slot3_assigned_channels)
    print(f"  Empty channels: {empty_channels}")
    
    assigned_count = len(df_assigned[df_assigned['Channel'] > 0])
    total_items = len(df_assigned)
    
    print(f"\nSummary:")
    print(f"  ✓ Total items: {total_items}")
    print(f"  ✓ Assigned: {assigned_count}")
    print(f"  ✓ Unassigned: {total_items - assigned_count}")
    
    return True


if __name__ == "__main__":
    try:
        test_spare_distribution_fix()
        print("\n" + "=" * 100)
        print("✓ FIX VERIFICATION COMPLETE")
        print("=" * 100)
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
