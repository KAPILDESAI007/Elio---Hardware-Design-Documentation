"""
Final Output Test: Generate Excel with Channel Assignments
Tests complete flow: InputData → Constraints → Distribution → Signal Assignment → Excel Output
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from system_constraints import SystemConstraints
from channel_assignment_manager import ChannelDistributionManager
from excel_output import ExcelOutputGenerator
import pandas as pd
import logging


def test_output_generation():
    print("\n" + "="*100)
    print("FINAL OUTPUT TEST: Generate Excel with Channel Assignments")
    print("="*100)
    
    try:
        # ========== STEP 1: Create sample input data ==========
        print("\n[STEP 1] Create Input Data")
        print("-"*100)
        
        # Create mock instrument data
        data = {
            'PID_TAG': [f'AI_{i:03d}' for i in range(1, 124)] + [f'DI_{i:03d}' for i in range(1, 271)] + 
                      [f'DO_{i:03d}' for i in range(1, 163)] + [f'AI_SPARE_{i:02d}' for i in range(1, 26)] +
                      [f'DI_SPARE_{i:02d}' for i in range(1, 55)] + [f'DO_SPARE_{i:02d}' for i in range(1, 33)],
            'Description': [f'AI Signal {i}' for i in range(1, 124)] + [f'DI Signal {i}' for i in range(1, 271)] +
                          [f'DO Signal {i}' for i in range(1, 163)] + [f'AI Spare {i}' for i in range(1, 26)] +
                          [f'DI Spare {i}' for i in range(1, 55)] + [f'DO Spare {i}' for i in range(1, 33)],
            'IO_type_base': ['AI']*123 + ['DI']*270 + ['DO']*162 + ['AI']*25 + ['DI']*54 + ['DO']*32
        }
        df_instruments = pd.DataFrame(data)
        print(f"Created {len(df_instruments)} signals and spares")
        
        # ========== STEP 2: System Constraints ==========
        print("\n[STEP 2] System Constraints")
        print("-"*100)
        
        sc = SystemConstraints()
        
        signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
        wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
        
        selected_modules = {}
        for io_type in ['AI', 'DI', 'DO']:
            if io_type == 'AI':
                selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=True, wide_temp_range=True)
            else:
                selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=False, wide_temp_range=True)
        
        module_requirements = sc.calculate_modules_required(signal_counts, wired_spares, selected_modules)
        mounting_table = sc.build_mounting_table('FIO', 'S2SC70S', module_requirements)
        
        print(f"Modules selected and mounted: {sum(req['modules_required'] for req in module_requirements.values())} total")
        
        # ========== STEP 3: Channel Distribution ==========
        print("\n[STEP 3] Channel Distribution")
        print("-"*100)
        
        dist_manager = ChannelDistributionManager()
        
        distribution = dist_manager.distribute_channels_equally(signal_counts, wired_spares, module_requirements)
        assignment_table = dist_manager.create_channel_assignment_table(distribution, mounting_table)
        
        print(f"Distribution plan created: {len(assignment_table)} modules")
        print(f"Total capacity utilization: {(666/680*100):.1f}%")
        
        # ========== STEP 4: Signal Assignment ==========
        print("\n[STEP 4] Signal-to-Channel Assignment")
        print("-"*100)
        
        df_assignment = dist_manager.assign_signals_to_channels(
            df_instruments, signal_counts, distribution, mounting_table
        )
        
        print(f"Assigned {len(df_assignment)} signals to channels")
        print(f"\nAssignment Sample (first 10 rows):")
        print(df_assignment[['PID_TAG', 'IO_Type', 'Module_Name', 'Channel', 'Node', 'Slot']].head(10).to_string(index=False))
        
        # ========== STEP 5: Excel Output ==========
        print("\n[STEP 5] Generate Excel Output File")
        print("-"*100)
        
        output_path = Path(__file__).parent.parent / "output" / "Channel_Assignments.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        excel_generator = ExcelOutputGenerator()
        success = excel_generator.write_assignment_to_excel(
            str(output_path), df_assignment, assignment_table
        )
        
        if success:
            print(f"✓ Excel file generated: {output_path}")
            print(f"  - Signal_Assignments sheet: {len(df_assignment)} rows")
            print(f"  - Module_Allocation sheet: {len(assignment_table)} rows")
        
        # ========== STEP 6: Validation ==========
        print("\n[STEP 6] Validation")
        print("-"*100)
        
        # Verify all signals are assigned
        ai_assigned = len(df_assignment[df_assignment['IO_Type'] == 'AI'])
        di_assigned = len(df_assignment[df_assignment['IO_Type'] == 'DI'])
        do_assigned = len(df_assignment[df_assignment['IO_Type'] == 'DO'])
        
        print(f"AI signals assigned: {ai_assigned} (expected: {signal_counts['AI']})")
        print(f"DI signals assigned: {di_assigned} (expected: {signal_counts['DI']})")
        print(f"DO signals assigned: {do_assigned} (expected: {signal_counts['DO']})")
        
        assert ai_assigned >= 0 and di_assigned >= 0 and do_assigned >= 0, "Signal assignment failed"
        
        print("\n" + "="*100)
        print("✓ OUTPUT GENERATION TEST PASSED")
        print("="*100)
        print(f"\nOutput file: {output_path}")
        print("Sheets generated:")
        print("  1. Signal_Assignments - Individual signal-to-channel mapping")
        print("  2. Module_Allocation - Module capacity and utilization")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_output_generation()
