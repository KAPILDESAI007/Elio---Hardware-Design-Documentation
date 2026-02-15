"""
Test cases for SystemConstraints class.
Tests Yokogawa SIS system constraints including controller limits and module mounting rules.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from processors
sys.path.insert(0, str(Path(__file__).parent.parent))

from system_constraints import SystemConstraints


class TestSystemConstraints:
    """Test suite for SystemConstraints class."""
    
    @staticmethod
    def test_io_type_filter_fio():
        """TEST 1: Filter controllers supporting FIO."""
        print("\n" + "="*70)
        print("TEST 1: Filter controllers supporting FIO")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            filtered = sc.filter_by_io_type('FIO')
            
            assert len(filtered) > 0, "Should find FIO-supporting controllers"
            assert all(filtered['Supports_FIO'] == 'Yes'), "All controllers should support FIO"
            
            print(f"✓ TEST 1 PASSED: Found {len(filtered)} FIO-supporting controllers")
            return True
        except Exception as e:
            print(f"✗ TEST 1 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_io_type_filter_nio():
        """TEST 2: Filter controllers supporting NIO."""
        print("\n" + "="*70)
        print("TEST 2: Filter controllers supporting NIO")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            filtered = sc.filter_by_io_type('NIO')
            
            assert len(filtered) > 0, "Should find NIO-supporting controllers"
            assert all(filtered['Supports_NIO'] == 'Yes'), "All controllers should support NIO"
            
            print(f"✓ TEST 2 PASSED: Found {len(filtered)} NIO-supporting controllers")
            return True
        except Exception as e:
            print(f"✗ TEST 2 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_controller_model_filter():
        """TEST 3: Filter by specific controller model."""
        print("\n" + "="*70)
        print("TEST 3: Filter by specific controller model (S2SC70S, FIO)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            controller = sc.filter_by_controller_model('S2SC70S', 'FIO')
            
            assert controller['Controller_Model'] == 'S2SC70S', "Should return S2SC70S"
            assert controller['Supports_FIO'] == 'Yes', "Should support FIO"
            assert controller['Max_Safety_Nodes'] == 13, "Should have 13 safety nodes max"
            
            print(f"✓ TEST 3 PASSED: Controller {controller['Controller_Model']} retrieved")
            print(f"  - Max Safety Nodes: {controller['Max_Safety_Nodes']}")
            print(f"  - Max FIO Modules: {controller['Max_FIO_Modules']}")
            return True
        except Exception as e:
            print(f"✗ TEST 3 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_get_controller_limits():
        """TEST 4: Get full controller limits."""
        print("\n" + "="*70)
        print("TEST 4: Get full controller limits (S2SC70S, FIO)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            limits = sc.get_controller_limits('FIO', 'S2SC70S')
            
            required_keys = {
                'Controller_Model', 'System_Type', 'Supports_FIO', 'Supports_NIO',
                'Max_Safety_Nodes', 'Max_FIO_Modules', 'Max_Dual_Red_Modules'
            }
            assert required_keys.issubset(set(limits.keys())), "Missing required limit keys"
            
            print(f"✓ TEST 4 PASSED: Controller limits retrieved")
            print(f"  - Controller Model: {limits['Controller_Model']}")
            print(f"  - Max Safety Nodes: {limits['Max_Safety_Nodes']}")
            print(f"  - Max FIO Modules: {limits['Max_FIO_Modules']}")
            return True
        except Exception as e:
            print(f"✗ TEST 4 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_build_module_map_fio():
        """TEST 5: Build module map for FIO system."""
        print("\n" + "="*70)
        print("TEST 5: Build module map for FIO (S2SC70S)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            module_map = sc.build_module_map('FIO', 'S2SC70S')
            
            assert 'max_nodes' in module_map, "Missing max_nodes"
            assert 'nodes' in module_map, "Missing nodes"
            assert module_map['max_nodes'] == 13, "Should have 13 max nodes"
            
            print(f"✓ TEST 5 PASSED: Module map built")
            print(f"  - Max Nodes: {module_map['max_nodes']}")
            print(f"  - Node Configurations: {list(module_map['nodes'].keys())}")
            
            for node_key, node_config in module_map['nodes'].items():
                print(f"  - {node_key}: {len(node_config['iom_slots'])} IOM slots ({node_config['iom_slots']})")
            
            return True
        except Exception as e:
            print(f"✗ TEST 5 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_module_map_node_1_only():
        """TEST 6: Verify Node 1 Only configuration (single node)."""
        print("\n" + "="*70)
        print("TEST 6: Verify Node 1 Only configuration (single node system)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            module_map = sc.build_module_map('FIO', 'S2SC70S')
            
            if 'node_1_only' not in module_map['nodes']:
                raise ValueError("node_1_only configuration not found")
            
            node_1_only = module_map['nodes']['node_1_only']
            
            # Verify structure
            assert 'iom_slots' in node_1_only, "Missing iom_slots"
            assert 'total_iom_modules' in node_1_only, "Missing total_iom_modules"
            
            # For Node 1 Only, valid IOM slots should be 1-7 (8 is NaN)
            assert 8 not in node_1_only['iom_slots'], "Slot 8 should not have IOM (is NaN)"
            assert len(node_1_only['iom_slots']) == 7, "Should have 7 IOM slots (1-7)"
            assert node_1_only['iom_slots'] == [1, 2, 3, 4, 5, 6, 7], "IOM slots should be 1-7"
            
            print(f"✓ TEST 6 PASSED: Node 1 Only configuration validated")
            print(f"  - Total IOM Modules: {node_1_only['total_iom_modules']}")
            print(f"  - Valid IOM Slots: {node_1_only['iom_slots']}")
            print(f"  - Max Total Slots: {node_1_only['max_slots']}")
            return True
        except Exception as e:
            print(f"✗ TEST 6 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_module_map_node_2_onwards():
        """TEST 7: Verify Node 2+ configuration (multi-node)."""
        print("\n" + "="*70)
        print("TEST 7: Verify Node 2+ configuration (multi-node system)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            module_map = sc.build_module_map('FIO', 'S2SC70S')
            
            if 'node_2_onwards' not in module_map['nodes']:
                raise ValueError("node_2_onwards configuration not found")
            
            node_2_onwards = module_map['nodes']['node_2_onwards']
            
            # Verify structure
            assert 'iom_slots' in node_2_onwards, "Missing iom_slots"
            assert 'applicable_for_nodes' in node_2_onwards, "Missing applicable_for_nodes"
            
            # For Node 2+, valid IOM slots should be 1-8
            assert len(node_2_onwards['iom_slots']) == 8, "Should have 8 IOM slots (1-8)"
            assert node_2_onwards['iom_slots'] == [1, 2, 3, 4, 5, 6, 7, 8], "IOM slots should be 1-8"
            assert node_2_onwards['applicable_for_nodes'] == '2 to 13', "Should apply to nodes 2-13"
            
            print(f"✓ TEST 7 PASSED: Node 2+ configuration validated")
            print(f"  - Total IOM Modules: {node_2_onwards['total_iom_modules']}")
            print(f"  - Valid IOM Slots: {node_2_onwards['iom_slots']}")
            print(f"  - Applicable for Nodes: {node_2_onwards['applicable_for_nodes']}")
            return True
        except Exception as e:
            print(f"✗ TEST 7 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_validate_module_map():
        """TEST 8: Validate module map structure and constraints."""
        print("\n" + "="*70)
        print("TEST 8: Validate module map structure and constraints")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            module_map = sc.build_module_map('FIO', 'S2SC70S')
            
            # This should pass without raising exception
            is_valid = sc.validate_module_map(module_map)
            assert is_valid, "Module map should be valid"
            
            print(f"✓ TEST 8 PASSED: Module map validation successful")
            return True
        except Exception as e:
            print(f"✗ TEST 8 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_mounting_arrangement_summary():
        """TEST 9: Summary of mounting arrangement for complete system."""
        print("\n" + "="*70)
        print("TEST 9: Complete mounting arrangement summary (S2SC70S, FIO)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            limits = sc.get_controller_limits('FIO', 'S2SC70S')
            module_map = sc.build_module_map('FIO', 'S2SC70S')
            
            print(f"\nSystem Configuration:")
            print(f"  Controller: {limits['Controller_Model']}")
            print(f"  System Type: {limits['System_Type']}")
            print(f"  Max Safety Nodes: {module_map['max_nodes']}")
            print(f"\nNode Configurations:")
            
            total_slots = 0
            total_iom_modules = 0
            
            for node_key, node_config in module_map['nodes'].items():
                print(f"\n  {node_config['node_type']}:")
                print(f"    - Slots per Node: {node_config['max_slots']}")
                print(f"    - IOM Module Slots: {node_config['iom_slots']}")
                print(f"    - Total IOM Modules per Node: {node_config['total_iom_modules']}")
                
                if 'applicable_for_nodes' in node_config:
                    print(f"    - Applicable for Nodes: {node_config['applicable_for_nodes']}")
                    # Calculate for multiple nodes
                    num_multi_nodes = module_map['max_nodes'] - 1  # Subtract Node 1
                    total_iom_modules += node_config['total_iom_modules'] * num_multi_nodes
                else:
                    total_iom_modules += node_config['total_iom_modules']
                
                total_slots += node_config['max_slots']
            
            print(f"\nSystem-wide Summary:")
            print(f"  Total IOM Module Slots Available: {total_iom_modules}")
            print(f"  Max FIO Modules (from limits): {limits['Max_FIO_Modules']}")
            
            assert module_map['max_nodes'] == 13, "Max nodes should be 13"
            assert total_iom_modules > 0, "Should have at least some IOM slots"
            
            print(f"\n✓ TEST 9 PASSED: Complete mounting arrangement verified")
            return True
        except Exception as e:
            print(f"✗ TEST 9 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_fio_ai_basic():
        """TEST 10: Select IO module for FIO AI type with HART (to get single module)."""
        print("\n" + "="*70)
        print("TEST 10: Select IO module for FIO/AI with HART support")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            # Need HART to narrow down to single module (SAI143-H)
            module = sc.select_io_module('FIO', 'AI', requires_hart=True, wide_temp_range=False)
            
            assert module['Module'] is not None, "Module name should exist"
            assert module['Usable_Channels'] > 0, "Should have usable channels"
            assert module['Family'] == 'FIO', "Should be FIO family"
            assert module['IO_Type'] == 'AI', "Should be AI type"
            assert module['Supports_HART'] == 'Yes', "Should support HART"
            
            print(f"✓ TEST 10 PASSED: FIO/AI HART module selected")
            print(f"  - Module: {module['Module']}")
            print(f"  - Usable Channels: {module['Usable_Channels']}")
            print(f"  - Max Temp: {module['Ambient_Max_C']}°C")
            print(f"  - Wiring: {module['Wiring']}")
            return True
        except Exception as e:
            print(f"✗ TEST 10 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_with_hart():
        """TEST 11: Select IO module with HART and temperature filter."""
        print("\n" + "="*70)
        print("TEST 11: Select FIO/AI with HART and wide temp range (70°C)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            module = sc.select_io_module('FIO', 'AI', requires_hart=True, wide_temp_range=True)
            
            assert module['Module'] is not None, "Module name should exist"
            assert module['Supports_HART'] == 'Yes', "Should have HART support"
            assert module['Family'] == 'FIO', "Should be FIO family"
            assert module['IO_Type'] == 'AI', "Should be AI type"
            assert module['Ambient_Max_C'] == 70, "Should have 70°C rating"
            
            print(f"✓ TEST 11 PASSED: FIO/AI HART 70°C module selected")
            print(f"  - Module: {module['Module']}")
            print(f"  - HART Support: {module['Supports_HART']}")
            print(f"  - Usable Channels: {module['Usable_Channels']}")
            print(f"  - Max Temp: {module['Ambient_Max_C']}°C")
            print(f"  - Wiring: {module['Wiring']}")
            return True
        except Exception as e:
            print(f"✗ TEST 11 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_wide_temp_range():
        """TEST 12: Select IO module with wide temperature range - DI type (single module)."""
        print("\n" + "="*70)
        print("TEST 12: Select IO module for FIO/DI with wide temp range (70°C)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            # DI at 70C has only one module (SDV144-S)
            module = sc.select_io_module('FIO', 'DI', requires_hart=False, wide_temp_range=True)
            
            assert module['Module'] is not None, "Module name should exist"
            assert module['Ambient_Max_C'] == 70, "Should have 70°C rating for wide temp range"
            assert module['Family'] == 'FIO', "Should be FIO family"
            assert module['Usable_Channels'] > 0, "Should have usable channels"
            
            print(f"✓ TEST 12 PASSED: FIO/DI wide temp module selected")
            print(f"  - Module: {module['Module']}")
            print(f"  - Max Ambient Temp: {module['Ambient_Max_C']}°C")
            print(f"  - Usable Channels: {module['Usable_Channels']}")
            print(f"  - Wiring: {module['Wiring']}")
            return True
        except Exception as e:
            print(f"✗ TEST 12 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_multiple_results_fail():
        """TEST 13: Module selection fails when multiple different modules found (negative test)."""
        print("\n" + "="*70)
        print("TEST 13: Module selection should fail - multiple modules (negative test)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            # Try to select AI module without temperature or HART filter 
            # This will have both SAI143-S and SAI143-H modules
            module = sc.select_io_module('FIO', 'AI', requires_hart=False, wide_temp_range=False)
            
            # If we get here, multiple modules weren't found - test might pass by accident
            print(f"✗ TEST 13 FAILED: Should have raised ValueError for multiple modules")
            print(f"   Got single module: {module['Module']}")
            return False
        except ValueError as e:
            if "Multiple different modules found" in str(e):
                print(f"✓ TEST 13 PASSED: Correctly detected multiple different modules")
                print(f"  - Error message: {e}")
                return True
            else:
                print(f"✗ TEST 13 FAILED: Wrong error - {e}")
                return False
        except Exception as e:
            print(f"✗ TEST 13 FAILED: Unexpected error - {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_no_results_fail():
        """TEST 14: Module selection fails when no results found (negative test)."""
        print("\n" + "="*70)
        print("TEST 14: Module selection should fail - no results (negative test)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            # Try invalid IO type
            module = sc.select_io_module('FIO', 'INVALID_TYPE', requires_hart=False)
            print(f"✗ TEST 14 FAILED: Should have raised ValueError for invalid IO type")
            return False
        except ValueError as e:
            if "Invalid IO type" in str(e):
                print(f"✓ TEST 14 PASSED: Correctly rejected invalid IO type")
                print(f"  - Error message: {e}")
                return True
            else:
                print(f"✗ TEST 14 FAILED: Wrong error - {e}")
                return False
        except Exception as e:
            print(f"✗ TEST 14 FAILED: Unexpected error type - {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_all_io_types():
        """TEST 15: Verify module selection works for all supported IO types with temp filter."""
        print("\n" + "="*70)
        print("TEST 15: Module selection for all FIO IO types (70°C)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            io_types = ['AI', 'DI', 'DO']
            modules_found = {}
            
            for io_type in io_types:
                try:
                    # Use both HART and temp filter for AI to get single module
                    if io_type == 'AI':
                        module = sc.select_io_module('FIO', io_type, requires_hart=True, wide_temp_range=True)
                    else:
                        module = sc.select_io_module('FIO', io_type, requires_hart=False, wide_temp_range=True)
                    modules_found[io_type] = module['Module']
                    print(f"  - {io_type}: {module['Module']} ({module['Usable_Channels']} channels)")
                except ValueError as e:
                    print(f"  - {io_type}: Not available")
            
            assert len(modules_found) > 0, "Should find at least some IO type modules"
            
            print(f"\n✓ TEST 15 PASSED: Module selection verified for FIO IO types")
            print(f"  - Found {len(modules_found)}/{len(io_types)} IO type modules")
            return True
        except Exception as e:
            print(f"✗ TEST 15 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_select_io_module_info_completeness():
        """TEST 16: Verify selected module info has all required fields."""
        print("\n" + "="*70)
        print("TEST 16: Verify module info completeness (FIO/DI, 70°C)")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            # Use DI which has single module at 70C
            module = sc.select_io_module('FIO', 'DI', requires_hart=False, wide_temp_range=True)
            
            required_keys = {
                'Module', 'Usable_Channels', 'Family', 'IO_Type',
                'Supports_HART', 'Ambient_Max_C', 'Signal_Type', 'Nominal_Channels', 'Wiring'
            }
            
            missing_keys = required_keys - set(module.keys())
            assert len(missing_keys) == 0, f"Missing keys: {missing_keys}"
            
            # Validate types and values
            assert isinstance(module['Module'], str) and len(module['Module']) > 0, "Module should be non-empty string"
            assert isinstance(module['Usable_Channels'], int) and module['Usable_Channels'] > 0, "Channels should be positive int"
            assert module['Family'] in ['FIO', 'NIO'], "Family must be FIO or NIO"
            assert module['IO_Type'] in ['AI', 'DI', 'DO', 'AO', 'SOFT', 'Baseplate'], "IO_Type must be valid"
            assert module['Supports_HART'] in ['Yes', 'No'], "HART support must be Yes/No"
            assert isinstance(module['Ambient_Max_C'], int) and module['Ambient_Max_C'] > 0, "Temp should be positive int"
            assert 'Wiring' in module and module['Wiring'] is not None, "Wiring should exist"
            
            print(f"✓ TEST 16 PASSED: Module info is complete and valid")
            print(f"  - Module: {module['Module']}")
            print(f"  - Family: {module['Family']}")
            print(f"  - IO_Type: {module['IO_Type']}")
            print(f"  - Usable_Channels: {module['Usable_Channels']}")
            print(f"  - Ambient_Max_C: {module['Ambient_Max_C']}°C")
            print(f"  - Wiring: {module['Wiring']}")
            return True
        except Exception as e:
            print(f"✗ TEST 16 FAILED: {e}")
            return False
    
    
    @staticmethod
    def test_calculate_modules_required():
        """TEST 17: Calculate modules required based on signals and spares."""
        print("\n" + "="*70)
        print("TEST 17: Calculate modules required for each IO type")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            
            # Simulate instrument data from input_data_analysis
            signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
            wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
            
            # Select modules for each IO type
            selected_modules = {}
            for io_type in ['AI', 'DI', 'DO']:
                if io_type == 'AI':
                    selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=True, wide_temp_range=True)
                else:
                    selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=False, wide_temp_range=True)
            
            # Calculate modules required
            requirements = sc.calculate_modules_required(signal_counts, wired_spares, selected_modules)
            
            # Verify structure
            assert 'AI' in requirements, "AI should be in requirements"
            assert 'DI' in requirements, "DI should be in requirements"
            assert 'DO' in requirements, "DO should be in requirements"
            
            # Verify AI calculations
            ai_req = requirements['AI']
            assert ai_req['signals'] == 123, "AI signals should be 123"
            assert ai_req['wired_spares'] == 25, "AI wired spares should be 25"
            assert ai_req['total_channels_required'] == 148, "AI total should be 148"
            assert ai_req['modules_required'] > 0, "AI should need at least 1 module"
            assert ai_req['spare_capacity'] >= 0, "Spare capacity should be non-negative"
            
            # Verify DI calculations
            di_req = requirements['DI']
            assert di_req['signals'] == 270, "DI signals should be 270"
            assert di_req['wired_spares'] == 54, "DI wired spares should be 54"
            assert di_req['total_channels_required'] == 324, "DI total should be 324"
            
            # Verify DO calculations
            do_req = requirements['DO']
            assert do_req['signals'] == 162, "DO signals should be 162"
            assert do_req['wired_spares'] == 32, "DO wired spares should be 32"
            assert do_req['total_channels_required'] == 194, "DO total should be 194"
            
            print(f"✓ TEST 17 PASSED: Module requirements calculated correctly")
            for io_type in ['AI', 'DI', 'DO']:
                req = requirements[io_type]
                print(f"  - {io_type}: {req['signals']} signals + {req['wired_spares']} spares = {req['total_channels_required']} channels")
                print(f"    * {req['modules_required']} x {req['module_name']} ({req['usable_channels_per_module']} ch/module)")
                print(f"    * {req['channels_available']} channels available, {req['spare_capacity']} spare slots")
            return True
        except Exception as e:
            print(f"✗ TEST 17 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def test_build_mounting_table():
        """TEST 18: Build mounting table with module placement."""
        print("\n" + "="*70)
        print("TEST 18: Build mounting table for module placement")
        print("-"*70)
        
        try:
            sc = SystemConstraints()
            
            # Get modules and calculate requirements
            signal_counts = {'AI': 123, 'DI': 270, 'DO': 162}
            wired_spares = {'AI': 25, 'DI': 54, 'DO': 32}
            
            selected_modules = {}
            for io_type in ['AI', 'DI', 'DO']:
                if io_type == 'AI':
                    selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=True, wide_temp_range=True)
                else:
                    selected_modules[io_type] = sc.select_io_module('FIO', io_type, requires_hart=False, wide_temp_range=True)
            
            requirements = sc.calculate_modules_required(signal_counts, wired_spares, selected_modules)
            
            # Build mounting table
            mounting_table = sc.build_mounting_table('FIO', 'S2SC70S', requirements)
            
            # Verify table structure
            assert isinstance(mounting_table, __import__('pandas').DataFrame), "Should return DataFrame"
            assert mounting_table.shape[0] == 13, "Should have 13 nodes"
            assert mounting_table.shape[1] == 12, "Should have 12 slots"
            
            # Verify node names
            expected_nodes = [f'Node_{i}' for i in range(1, 14)]
            assert list(mounting_table.index) == expected_nodes, "Node names should be Node_1 to Node_13"
            
            # Verify slot names
            expected_slots = [f'Slot_{i}' for i in range(1, 13)]
            assert list(mounting_table.columns) == expected_slots, "Slot names should be Slot_1 to Slot_12"
            
            # Verify modules are placed
            total_modules = mounting_table.count().sum()
            total_modules_required = sum(req['modules_required'] for req in requirements.values())
            assert total_modules == total_modules_required, \
                f"Should have {total_modules_required} modules placed, got {total_modules}"
            
            print(f"✓ TEST 18 PASSED: Mounting table built correctly")
            print(f"  - Table shape: {mounting_table.shape[0]} nodes x {mounting_table.shape[1]} slots")
            print(f"  - Total modules placed: {total_modules}")
            print(f"\nSample mounting table (first 3 nodes):")
            print(mounting_table.head(3).to_string())
            return True
        except Exception as e:
            print(f"✗ TEST 18 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def run_all_tests():
        """Run all test cases."""
        print("\n\n" + "="*70)
        print("SYSTEM CONSTRAINTS TEST SUITE")
        print("="*70)
        
        tests = [
            TestSystemConstraints.test_io_type_filter_fio,
            TestSystemConstraints.test_io_type_filter_nio,
            TestSystemConstraints.test_controller_model_filter,
            TestSystemConstraints.test_get_controller_limits,
            TestSystemConstraints.test_build_module_map_fio,
            TestSystemConstraints.test_module_map_node_1_only,
            TestSystemConstraints.test_module_map_node_2_onwards,
            TestSystemConstraints.test_validate_module_map,
            TestSystemConstraints.test_mounting_arrangement_summary,
            TestSystemConstraints.test_select_io_module_fio_ai_basic,
            TestSystemConstraints.test_select_io_module_with_hart,
            TestSystemConstraints.test_select_io_module_wide_temp_range,
            TestSystemConstraints.test_select_io_module_multiple_results_fail,
            TestSystemConstraints.test_select_io_module_no_results_fail,
            TestSystemConstraints.test_select_io_module_all_io_types,
            TestSystemConstraints.test_select_io_module_info_completeness,
            TestSystemConstraints.test_calculate_modules_required,
            TestSystemConstraints.test_build_mounting_table,
        ]
        
        results = []
        for test in tests:
            results.append(test())
        
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        total = len(results)
        passed = sum(results)
        failed = total - passed
        
        print(f"Tests run: {total}")
        print(f"Successes: {passed}")
        print(f"Failures: {failed}")
        print("="*70)
        
        if failed == 0:
            print("\n✓ ALL TESTS PASSED!\n")
        else:
            print(f"\n✗ {failed} TEST(S) FAILED!\n")
        
        return failed == 0


if __name__ == "__main__":
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    TestSystemConstraints.run_all_tests()
