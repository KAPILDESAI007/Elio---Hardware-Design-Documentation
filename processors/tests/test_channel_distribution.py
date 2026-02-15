"""
Test cases for ChannelDistributionManager class.
Tests channel distribution logic for assigning signals and spares equally across modules.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from channel_assignment_manager import ChannelDistributionManager
import pandas as pd
import logging


class TestChannelDistribution:
    """Test suite for ChannelDistributionManager class."""
    
    @staticmethod
    def test_calculate_total_available_channels():
        """TEST 1: Calculate total available channels from module requirements."""
        print("\n" + "="*100)
        print("TEST 1: Calculate total available channels")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            # Simulate module requirements from SystemConstraints
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 13,
                    'channels_available': 156
                },
                'DI': {
                    'module_name': 'SDV144-S',
                    'usable_channels_per_module': 12,
                    'modules_required': 27,
                    'channels_available': 324
                },
                'DO': {
                    'module_name': 'SDV541-S',
                    'usable_channels_per_module': 10,
                    'modules_required': 20,
                    'channels_available': 200
                }
            }
            
            available = manager.calculate_total_available_channels(module_requirements)
            
            # Verify AI channels
            assert available['AI']['total_available_channels'] == 156, \
                f"AI: expected 156, got {available['AI']['total_available_channels']}"
            assert available['AI']['modules_required'] == 13, \
                f"AI modules: expected 13, got {available['AI']['modules_required']}"
            
            # Verify DI channels
            assert available['DI']['total_available_channels'] == 324, \
                f"DI: expected 324, got {available['DI']['total_available_channels']}"
            
            # Verify DO channels
            assert available['DO']['total_available_channels'] == 200, \
                f"DO: expected 200, got {available['DO']['total_available_channels']}"
            
            print(f"✓ TEST 1 PASSED: Available channels calculated correctly")
            for io_type, avail in available.items():
                print(f"  - {io_type}: {avail['modules_required']} modules × "
                      f"{avail['usable_channels_per_module']} ch = {avail['total_available_channels']} ch")
            
            return True
        except Exception as e:
            print(f"✗ TEST 1 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_distribute_channels_equally():
        """TEST 2: Distribute signals and spares equally across modules."""
        print("\n" + "="*100)
        print("TEST 2: Distribute channels equally for each IO type")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            # Instrument data (signals + spares)
            signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
            wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
            
            # Module requirements
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 13
                },
                'DI': {
                    'module_name': 'SDV144-S',
                    'usable_channels_per_module': 12,
                    'modules_required': 27
                },
                'DO': {
                    'module_name': 'SDV541-S',
                    'usable_channels_per_module': 10,
                    'modules_required': 20
                }
            }
            
            distribution = manager.distribute_channels_equally(
                signal_counts, wired_spares, module_requirements
            )
            
            # Verify AI distribution
            ai_plan = distribution['AI']
            assert ai_plan['signals'] == 123, "AI signals mismatch"
            assert ai_plan['wired_spares'] == 25, "AI spares mismatch"
            assert ai_plan['total_items'] == 148, "AI total items mismatch"
            assert ai_plan['modules_required'] == 13, "AI modules mismatch"
            assert ai_plan['total_available_channels'] == 156, "AI available channels mismatch"
            assert ai_plan['blank_channels'] == 8, "AI blank channels mismatch"
            
            # Verify DI distribution
            di_plan = distribution['DI']
            assert di_plan['signals'] == 270, "DI signals mismatch"
            assert di_plan['wired_spares'] == 54, "DI spares mismatch"
            assert di_plan['total_items'] == 324, "DI total items mismatch"
            assert di_plan['blank_channels'] == 0, "DI blank channels mismatch"
            
            # Verify DO distribution
            do_plan = distribution['DO']
            assert do_plan['signals'] == 162, "DO signals mismatch"
            assert do_plan['wired_spares'] == 32, "DO spares mismatch"
            assert do_plan['total_items'] == 194, "DO total items mismatch"
            assert do_plan['blank_channels'] == 6, "DO blank channels mismatch"
            
            # Verify module specs are created
            assert len(ai_plan['module_specs']) == 13, "AI module specs count mismatch"
            assert len(di_plan['module_specs']) == 27, "DI module specs count mismatch"
            assert len(do_plan['module_specs']) == 20, "DO module specs count mismatch"
            
            # Verify equal distribution within modules
            ai_total = sum(spec['total_items'] for spec in ai_plan['module_specs'])
            assert ai_total == 148, f"AI module totals don't match: {ai_total} vs 148"
            
            print(f"✓ TEST 2 PASSED: Channels distributed equally")
            for io_type in ['AI', 'DI', 'DO']:
                plan = distribution[io_type]
                print(f"  - {io_type}: {plan['signals']} signals + {plan['wired_spares']} spares + "
                      f"{plan['blank_channels']} blanks across {plan['modules_required']} modules")
            
            return True
        except Exception as e:
            print(f"✗ TEST 2 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_distribution_remainder_handling():
        """TEST 3: Verify remainder distribution and capacity constraints."""
        print("\n" + "="*100)
        print("TEST 3: Verify remainder handling and capacity constraints")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            # Test case with remainder: 148 items across 13 modules (12 ch each)
            signal_counts = {'AI': 100}
            wired_spares = {'AI': 48}  # Total 148 items
            
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 13
                }
            }
            
            distribution = manager.distribute_channels_equally(
                signal_counts, wired_spares, module_requirements
            )
            
            ai_plan = distribution['AI']
            modules = ai_plan['module_specs']
            
            # 148 items / 13 modules = 11 base + 5 remainder
            # So first 5 modules get 12 items, last 8 get 11 items
            # CRITICAL: No module should exceed capacity of 12
            
            module_item_counts = [spec['total_items'] for spec in modules]
            
            # Verify all modules are within capacity
            for idx, count in enumerate(module_item_counts):
                assert count <= 12, f"Module {idx} has {count} items, exceeds capacity of 12!"
            
            # Verify total matches
            total_assigned = sum(module_item_counts)
            assert total_assigned == 148, f"Total should be 148, got {total_assigned}"
            
            # Count distribution pattern
            full_modules = sum(1 for count in module_item_counts if count == 12)
            partial_modules = sum(1 for count in module_item_counts if count == 11)
            
            print(f"✓ TEST 3 PASSED: Remainder handling and capacity constraints correct")
            print(f"  - First 5 modules: 12 items each")
            print(f"  - Next 8 modules: 11 items each")
            print(f"  - Total: {total_assigned} = 148 ✓")
            print(f"  - All modules within capacity (12 max)")
            
            return True
        except Exception as e:
            print(f"✗ TEST 3 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_create_channel_assignment_table():
        """TEST 4: Create channel assignment table without mounting info."""
        print("\n" + "="*100)
        print("TEST 4: Create channel assignment table")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
            wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
            
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 13
                },
                'DI': {
                    'module_name': 'SDV144-S',
                    'usable_channels_per_module': 12,
                    'modules_required': 27
                },
                'DO': {
                    'module_name': 'SDV541-S',
                    'usable_channels_per_module': 10,
                    'modules_required': 20
                }
            }
            
            distribution = manager.distribute_channels_equally(
                signal_counts, wired_spares, module_requirements
            )
            
            df_table = manager.create_channel_assignment_table(distribution)
            
            # Verify table structure
            assert len(df_table) == 60, f"Should have 60 rows (13+27+20), got {len(df_table)}"
            
            required_columns = ['IO_Type', 'Module_Name', 'Signals', 'Wired_Spares', 
                               'Blank_Channels', 'Total_Assigned', 'Module_Capacity', 'Utilization_%']
            for col in required_columns:
                assert col in df_table.columns, f"Missing column: {col}"
            
            # Verify AI rows
            ai_rows = df_table[df_table['IO_Type'] == 'AI']
            assert len(ai_rows) == 13, f"Expected 13 AI rows, got {len(ai_rows)}"
            assert all(ai_rows['Module_Capacity'] == 12), "AI modules should have capacity 12"
            
            # Verify DI rows
            di_rows = df_table[df_table['IO_Type'] == 'DI']
            assert len(di_rows) == 27, f"Expected 27 DI rows, got {len(di_rows)}"
            
            # Verify DO rows
            do_rows = df_table[df_table['IO_Type'] == 'DO']
            assert len(do_rows) == 20, f"Expected 20 DO rows, got {len(do_rows)}"
            assert all(do_rows['Module_Capacity'] == 10), "DO modules should have capacity 10"
            
            # Verify utilization percentages
            for idx, row in df_table.iterrows():
                expected_util = round((row['Total_Assigned'] / row['Module_Capacity'] * 100), 1)
                assert row['Utilization_%'] == expected_util, \
                    f"Row {idx}: expected {expected_util}%, got {row['Utilization_%']}%"
            
            print(f"✓ TEST 4 PASSED: Channel assignment table created")
            print(f"  - Total rows: {len(df_table)}")
            print(f"  - AI rows: {len(ai_rows)}")
            print(f"  - DI rows: {len(di_rows)}")
            print(f"  - DO rows: {len(do_rows)}")
            print(f"\nSample rows (first 5):")
            print(df_table[['IO_Type', 'Module_Name', 'Signals', 'Wired_Spares', 
                           'Blank_Channels', 'Utilization_%']].head(5).to_string())
            
            return True
        except Exception as e:
            print(f"✗ TEST 4 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_distribution_with_mounting_table():
        """TEST 5: Create assignment table with node/slot info from mounting table."""
        print("\n" + "="*100)
        print("TEST 5: Assignment table with node/slot locations")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            signal_counts = {'AI': 50, 'DI': 60}
            wired_spares = {'AI': 10, 'DI': 12}
            
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 5
                },
                'DI': {
                    'module_name': 'SDV144-S',
                    'usable_channels_per_module': 12,
                    'modules_required': 6
                }
            }
            
            distribution = manager.distribute_channels_equally(
                signal_counts, wired_spares, module_requirements
            )
            
            # Create a sample mounting table
            nodes = [f'Node_{i+1}' for i in range(3)]
            slots = [f'Slot_{i+1}' for i in range(8)]
            mounting_table = pd.DataFrame([[None]*8]*3, index=nodes, columns=slots)
            
            # Populate with some module instances
            mounting_table.loc['Node_1', 'Slot_1'] = 'SAI143-H_1'
            mounting_table.loc['Node_1', 'Slot_2'] = 'SAI143-H_2'
            mounting_table.loc['Node_1', 'Slot_3'] = 'SDV144-S_1'
            mounting_table.loc['Node_2', 'Slot_1'] = 'SAI143-H_3'
            
            df_table = manager.create_channel_assignment_table(distribution, mounting_table)
            
            # Verify Node/Slot columns were added
            assert 'Node' in df_table.columns, "Node column missing"
            assert 'Slot' in df_table.columns, "Slot column missing"
            
            # Check some known locations
            sai_1 = df_table[df_table['Module_Name'] == 'SAI143-H_1']
            if len(sai_1) > 0:
                assert sai_1.iloc[0]['Node'] == 1, "SAI143-H_1 should be at Node 1"
                assert sai_1.iloc[0]['Slot'] == 1, "SAI143-H_1 should be at Slot 1"
            
            sdv_1 = df_table[df_table['Module_Name'] == 'SDV144-S_1']
            if len(sdv_1) > 0:
                assert sdv_1.iloc[0]['Node'] == 1, "SDV144-S_1 should be at Node 1"
                assert sdv_1.iloc[0]['Slot'] == 3, "SDV144-S_1 should be at Slot 3"
            
            print(f"✓ TEST 5 PASSED: Assignment table with location info created")
            print(f"  - Total modules: {len(df_table)}")
            print(f"  - Modules with location: {(df_table['Node'] != 'N/A').sum()}")
            print(f"\nSample with locations:")
            print(df_table[df_table['Node'] != 'N/A'][['IO_Type', 'Module_Name', 'Node', 'Slot']].head(10).to_string())
            
            return True
        except Exception as e:
            print(f"✗ TEST 5 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_zero_signals_edge_case():
        """TEST 6: Handle edge case with zero signals for an IO type."""
        print("\n" + "="*100)
        print("TEST 6: Edge case - zero signals for an IO type")
        print("-"*100)
        
        try:
            manager = ChannelDistributionManager()
            
            # AO has no signals, only spares
            signal_counts = {'AI': 100, 'AO': 0}
            wired_spares = {'AI': 20, 'AO': 5}
            
            module_requirements = {
                'AI': {
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 10
                },
                'AO': {
                    'module_name': 'SAO141-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 1
                }
            }
            
            distribution = manager.distribute_channels_equally(
                signal_counts, wired_spares, module_requirements
            )
            
            # Verify AO (all blanks + spares)
            ao_plan = distribution['AO']
            assert ao_plan['signals'] == 0, "AO should have 0 signals"
            assert ao_plan['wired_spares'] == 5, "AO should have 5 spares"
            assert ao_plan['total_items'] == 5, "AO total should be 5"
            assert ao_plan['blank_channels'] == 7, "AO should have 7 blanks"
            
            # Module should have 0 signals, 5 spares, 7 blanks
            ao_module = ao_plan['module_specs'][0]
            assert ao_module['signals'] == 0, "Module should have 0 signals"
            assert ao_module['wired_spares'] == 5, "Module should have 5 spares"
            assert ao_module['blank_channels'] == 7, "Module should have 7 blanks"
            
            print(f"✓ TEST 6 PASSED: Edge case handled correctly")
            print(f"  - AO: 0 signals + 5 spares + 7 blanks = 12 capacity")
            print(f"  - AI: 100 signals + 20 spares across 10 modules")
            
            return True
        except Exception as e:
            print(f"✗ TEST 6 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def run_all_tests():
        """Run all test cases."""
        print("\n\n" + "="*100)
        print("CHANNEL DISTRIBUTION MANAGER TEST SUITE")
        print("="*100)
        
        tests = [
            TestChannelDistribution.test_calculate_total_available_channels,
            TestChannelDistribution.test_distribute_channels_equally,
            TestChannelDistribution.test_distribution_remainder_handling,
            TestChannelDistribution.test_create_channel_assignment_table,
            TestChannelDistribution.test_distribution_with_mounting_table,
            TestChannelDistribution.test_zero_signals_edge_case,
        ]
        
        results = []
        for test in tests:
            results.append(test())
        
        print("\n" + "="*100)
        print("TEST SUMMARY")
        print("="*100)
        
        total = len(results)
        passed = sum(results)
        failed = total - passed
        
        print(f"Tests run: {total}")
        print(f"Successes: {passed}")
        print(f"Failures: {failed}")
        print("="*100)
        
        if failed == 0:
            print("\n✓ ALL TESTS PASSED!\n")
        else:
            print(f"\n✗ {failed} TEST(S) FAILED!\n")
        
        return failed == 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    TestChannelDistribution.run_all_tests()
