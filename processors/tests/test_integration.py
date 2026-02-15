"""
Integration Test: SystemConstraints → ChannelDistribution
Tests the complete flow of module selection and channel distribution
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from system_constraints import SystemConstraints
from channel_assignment_manager import ChannelDistributionManager
import logging


def test_integration():
    """Test complete flow from constraints to channel distribution."""
    print("\n" + "="*100)
    print("INTEGRATION TEST: SystemConstraints → ChannelDistribution")
    print("="*100)
    
    try:
        # ========== STEP 1: System Constraints ==========
        print("\n[STEP 1] System Constraints - Module Selection & Mounting")
        print("-"*100)
        
        sc = SystemConstraints()
        
        # Simulate data from InputDataAnalyzer
        signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
        wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
        
        print(f"Input signals: {signal_counts}")
        print(f"Input spares: {wired_spares}")
        
        # Select modules
        selected_modules = {}
        for io_type in ['AI', 'DI', 'DO']:
            if io_type == 'AI':
                selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=True, wide_temp_range=True)
            else:
                selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=False, wide_temp_range=True)
        
        print(f"\nSelected modules:")
        for io_type, module in selected_modules.items():
            print(f"  {io_type}: {module['Module']} ({module['Usable_Channels']} ch)")
        
        # Calculate modules required
        module_requirements = sc.calculate_modules_required(signal_counts, wired_spares, selected_modules)
        print(f"\nModule requirements calculated:")
        for io_type, req in module_requirements.items():
            print(f"  {io_type}: {req['modules_required']} modules @ {req['usable_channels_per_module']} ch/module")
        
        # Build mounting table
        mounting_table = sc.build_mounting_table('FIO', 'S2SC70S', module_requirements)
        print(f"\nMounting table: {mounting_table.shape[0]} nodes × {mounting_table.shape[1]} slots")
        print(f"Sample (first 3 nodes):")
        print(mounting_table.head(3).to_string())
        
        # ========== STEP 2: Channel Distribution ==========
        print("\n\n[STEP 2] Channel Distribution - Equal Channel Allocation")
        print("-"*100)
        
        dist_manager = ChannelDistributionManager()
        
        # Calculate available channels
        available_channels = dist_manager.calculate_total_available_channels(module_requirements)
        print(f"Total available channels per IO type:")
        for io_type, avail in available_channels.items():
            print(f"  {io_type}: {avail['total_available_channels']} channels")
        
        # Distribute channels
        distribution = dist_manager.distribute_channels_equally(signal_counts, wired_spares, module_requirements)
        
        print(f"\nDistribution plan created:")
        for io_type, plan in distribution.items():
            print(f"  {io_type}:")
            print(f"    - {plan['signals']} signals + {plan['wired_spares']} spares = {plan['total_items']} items")
            print(f"    - {plan['modules_required']} modules × {plan['channels_per_module']} channels")
            print(f"    - {plan['blank_channels']} blank channels")
        
        # Create assignment table
        assignment_table = dist_manager.create_channel_assignment_table(distribution, mounting_table)
        print(f"\nChannel assignment table created: {len(assignment_table)} module entries")
        print(f"Columns: {list(assignment_table.columns)}")
        
        # ========== STEP 3: Validation ==========
        print("\n\n[STEP 3] Validation")
        print("-"*100)
        
        # Verify totals
        total_signals_placed = assignment_table['Signals'].sum()
        total_spares_placed = assignment_table['Wired_Spares'].sum()
        total_items_placed = assignment_table['Total_Assigned'].sum()
        total_blank = assignment_table['Blank_Channels'].sum()
        
        print(f"Signals placed: {total_signals_placed} (expected: {sum(signal_counts.values())})")
        assert total_signals_placed == sum(signal_counts.values()), "Signal count mismatch!"
        
        print(f"Spares placed: {total_spares_placed} (expected: {sum(wired_spares.values())})")
        assert total_spares_placed == sum(wired_spares.values()), "Spare count mismatch!"
        
        print(f"Total items: {total_items_placed}")
        print(f"Total blank channels: {total_blank}")
        
        # Verify capacity not exceeded
        for idx, row in assignment_table.iterrows():
            if row['Total_Assigned'] > row['Module_Capacity']:
                print(f"\n✗ Row {idx}: Capacity exceeded!")
                print(f"  {row['Module_Name']}: {row['Total_Assigned']} assigned > {row['Module_Capacity']} capacity")
                print(f"  Signals: {row['Signals']}, Spares: {row['Wired_Spares']}, Blanks: {row['Blank_Channels']}")
                print(f"\nProblematic rows:")
                print(assignment_table.iloc[max(0, idx-2):min(len(assignment_table), idx+3)][
                    ['IO_Type', 'Module_Name', 'Signals', 'Wired_Spares', 'Blank_Channels', 'Total_Assigned', 'Module_Capacity']
                ].to_string())
            assert row['Total_Assigned'] <= row['Module_Capacity'], \
                f"Row {idx}: Total assigned ({row['Total_Assigned']}) exceeds capacity ({row['Module_Capacity']})!"
        
        print(f"\n✓ Capacity validation: All modules within limits")
        
        # Verify module distribution
        ai_count = assignment_table[assignment_table['IO_Type'] == 'AI'].shape[0]
        di_count = assignment_table[assignment_table['IO_Type'] == 'DI'].shape[0]
        do_count = assignment_table[assignment_table['IO_Type'] == 'DO'].shape[0]
        
        print(f"\n✓ Module distribution:")
        print(f"  - AI modules: {ai_count} (expected: 13)")
        print(f"  - DI modules: {di_count} (expected: 27)")
        print(f"  - DO modules: {do_count} (expected: 20)")
        
        assert ai_count == 13 and di_count == 27 and do_count == 20, "Module count mismatch!"
        
        # ========== STEP 4: Summary Output ==========
        print("\n\n[STEP 4] Summary Report")
        print("-"*100)
        print(dist_manager.get_distribution_summary(distribution))
        
        # ========== STEP 5: Sample Assignment Table ==========
        print("\n[STEP 5] Channel Assignment Table (Sample)")
        print("-"*100)
        print("\nFirst 10 module assignments:")
        print(assignment_table[['IO_Type', 'Module_Name', 'Signals', 'Wired_Spares', 
                               'Blank_Channels', 'Total_Assigned', 'Module_Capacity', 
                               'Utilization_%', 'Node', 'Slot']].head(10).to_string(index=False))
        
        print("\n\nAI Module Assignments:")
        ai_assignment = assignment_table[assignment_table['IO_Type'] == 'AI']
        print(ai_assignment[['Module_Name', 'Signals', 'Wired_Spares', 'Blank_Channels', 
                            'Utilization_%', 'Node', 'Slot']].to_string(index=False))
        
        # ========== FINAL STATUS ==========
        print("\n\n" + "="*100)
        print("✓ INTEGRATION TEST PASSED")
        print("="*100)
        print("\nComplete flow verified:")
        print("  ✓ InputDataAnalyzer data (signals + spares)")
        print("  ✓ SystemConstraints module selection & mounting")
        print("  ✓ ChannelDistributionManager equal distribution")
        print("  ✓ Channel assignment table generation")
        print("  ✓ Node/Slot location integration")
        print("  ✓ Capacity validation")
        print("  ✓ Total items verification")
        
        return True
        
    except Exception as e:
        print(f"\n✗ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_integration()
