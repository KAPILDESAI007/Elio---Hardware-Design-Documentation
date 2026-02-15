"""
System Constraints Module
Handles Yokogawa SIS system constraints including controller limits and module mounting rules.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Tuple


class SystemConstraints:
    """
    Main class for system constraints management.
    Reads and processes Yokogawa SIS constraints from Excel file.
    """
    
    def __init__(self):
        """Initialize SystemConstraints and load Excel data."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Determine template file path
        template_dir = Path(__file__).parent.parent / "templates"
        self.file_path = template_dir / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        # Load sheets
        try:
            self.controller_limits_df = pd.read_excel(self.file_path, sheet_name='Controller_Limits')
            self.mounting_rule_df = pd.read_excel(self.file_path, sheet_name='Mounting Rule')
            self.io_module_catalog_df = pd.read_excel(self.file_path, sheet_name='IO_Module_Catalog')
            self.logger.info("Successfully loaded constraint sheets")
        except Exception as e:
            self.logger.error(f"Error loading constraint sheets: {e}")
            raise
    
    
    def filter_by_io_type(self, io_type):
        """
        Filter controller options based on IO type (FIO or NIO).
        
        Args:
            io_type (str): 'FIO' or 'NIO'
            
        Returns:
            pd.DataFrame: Filtered controller rows that support the IO type
        """
        if io_type not in ['FIO', 'NIO']:
            raise ValueError(f"Invalid IO type: {io_type}. Must be 'FIO' or 'NIO'")
        
        if io_type == 'FIO':
            filtered_df = self.controller_limits_df[self.controller_limits_df['Supports_FIO'] == 'Yes'].copy()
        else:  # NIO
            filtered_df = self.controller_limits_df[self.controller_limits_df['Supports_NIO'] == 'Yes'].copy()
        
        self.logger.info(f"Filtered {len(filtered_df)} controllers supporting {io_type}")
        return filtered_df
    
    
    def filter_by_controller_model(self, controller_model, io_type):
        """
        Filter by controller model to get single row of constraints.
        
        Args:
            controller_model (str): Controller model name (e.g., 'S2SC70S', 'SCS60S')
            io_type (str): 'FIO' or 'NIO' to ensure compatibility
            
        Returns:
            pd.Series: Single row with controller constraints
            
        Raises:
            ValueError: If controller not found or doesn't support IO type
        """
        # First filter by IO type compatibility
        filtered_df = self.filter_by_io_type(io_type)
        
        # Then filter by model
        model_rows = filtered_df[filtered_df['Controller_Model'] == controller_model]
        
        if len(model_rows) == 0:
            raise ValueError(f"Controller model {controller_model} not found or doesn't support {io_type}")
        
        if len(model_rows) > 1:
            self.logger.warning(f"Multiple rows found for {controller_model}. Returning first row.")
        
        self.logger.info(f"Selected controller: {controller_model}")
        return model_rows.iloc[0]
    
    
    def get_controller_limits(self, io_type, controller_model):
        """
        Get all controller limits for specified IO type and model.
        
        Args:
            io_type (str): 'FIO' or 'NIO'
            controller_model (str): Controller model name
            
        Returns:
            dict: Dictionary with controller constraints (Max_Safety_Nodes, Max_FIO_Modules, etc.)
        """
        controller_row = self.filter_by_controller_model(controller_model, io_type)
        
        limits = {
            'Controller_Model': controller_row['Controller_Model'],
            'System_Type': controller_row['System_Type'],
            'Supports_NIO': controller_row['Supports_NIO'],
            'Supports_FIO': controller_row['Supports_FIO'],
            'Max_Safety_Nodes': controller_row['Max_Safety_Nodes'],
            'Max_FIO_Modules': controller_row['Max_FIO_Modules'],
            'Max_Dual_Red_Modules': controller_row['Max_Dual_Red_Modules'],
        }
        
        if io_type == 'NIO':
            limits['Max_NIU_Nodes'] = controller_row['Max_NIU_Nodes']
            limits['Max_NIO_IO_Units'] = controller_row['Max_NIO_IO_Units']
        
        return limits
    
    
    def build_module_map(self, io_type, controller_model):
        """
        Build module mounting map based on controller constraints and mounting rules.
        
        Creates mapping of node configurations with valid IO module slots.
        Supports up to Max_Safety_Nodes nodes in the system.
        
        Args:
            io_type (str): 'FIO' or 'NIO'
            controller_model (str): Controller model name
            
        Returns:
            dict: Module map with node configurations and valid module slots
                Structure:
                {
                    'max_nodes': int,
                    'nodes': {
                        'node_1': {'node_type': str, 'iom_slots': [list of IOM slots]},
                        'node_2_onwards': {'node_type': str, 'iom_slots': [list of IOM slots]},
                        ...
                    }
                }
        """
        # Get controller limits
        limits = self.get_controller_limits(io_type, controller_model)
        max_nodes = limits['Max_Safety_Nodes']
        
        module_map = {
            'max_nodes': max_nodes,
            'nodes': {}
        }
        
        # Get mounting rules - Node 1 Only (single node system)
        node_1_only_rules = self.mounting_rule_df[
            self.mounting_rule_df['Node No'] == 'Node 1 Only'
        ]
        
        # Get mounting rules - Node 1 (multi-node system, first node)
        node_1_rules = self.mounting_rule_df[
            self.mounting_rule_df['Node No'] == 1
        ]
        
        # Get mounting rules - Node > 1 (multi-node system, additional nodes)
        node_multi_rules = self.mounting_rule_df[
            self.mounting_rule_df['Node No'] == '>1'
        ]
        
        # Build Node 1 Only configuration (single node)
        if len(node_1_only_rules) > 0:
            iom_slots = node_1_only_rules[
                node_1_only_rules['Type'] == 'IOM'
            ]['Slot'].tolist()
            
            module_map['nodes']['node_1_only'] = {
                'node_type': 'Single Node (Node 1 Only)',
                'max_slots': max(node_1_only_rules['Slot'].max(), 0),
                'iom_slots': sorted(iom_slots),
                'total_iom_modules': len(iom_slots)
            }
        
        # Build Node 1 configuration for multi-node (if different from single node)
        if len(node_1_rules) > 0:
            iom_slots = node_1_rules[
                node_1_rules['Type'] == 'IOM'
            ]['Slot'].tolist()
            
            module_map['nodes']['node_1'] = {
                'node_type': 'Multi-Node First Node',
                'max_slots': max(node_1_rules['Slot'].max(), 0),
                'iom_slots': sorted(iom_slots),
                'total_iom_modules': len(iom_slots)
            }
        
        # Build Node 2+ configuration for multi-node systems
        if len(node_multi_rules) > 0 and max_nodes > 1:
            iom_slots = node_multi_rules[
                node_multi_rules['Type'] == 'IOM'
            ]['Slot'].tolist()
            
            module_map['nodes']['node_2_onwards'] = {
                'node_type': 'Multi-Node Additional Nodes',
                'max_slots': max(node_multi_rules['Slot'].max(), 0),
                'iom_slots': sorted(iom_slots),
                'total_iom_modules': len(iom_slots),
                'applicable_for_nodes': f'2 to {max_nodes}'
            }
        
        self.logger.info(f"Built module map for {controller_model}: max {max_nodes} safety nodes")
        return module_map
    
    
    def validate_module_map(self, module_map):
        """
        Validate that module map has correct structure and slot configurations.
        
        Args:
            module_map (dict): Module map from build_module_map()
            
        Returns:
            bool: True if valid, raises exception otherwise
        """
        if 'max_nodes' not in module_map:
            raise ValueError("Missing 'max_nodes' in module map")
        
        if 'nodes' not in module_map:
            raise ValueError("Missing 'nodes' in module map")
        
        if not isinstance(module_map['nodes'], dict):
            raise ValueError("'nodes' must be a dictionary")
        
        # Validate each node configuration
        valid_keys = {'node_1_only', 'node_1', 'node_2_onwards'}
        for node_key in module_map['nodes'].keys():
            if node_key not in valid_keys:
                raise ValueError(f"Invalid node key: {node_key}")
            
            node_config = module_map['nodes'][node_key]
            required_keys = {'node_type', 'max_slots', 'iom_slots', 'total_iom_modules'}
            if not required_keys.issubset(node_config.keys()):
                raise ValueError(f"Node {node_key} missing required keys: {required_keys - set(node_config.keys())}")
            
            # Validate IOM slots are within max_slots
            if node_config['iom_slots']:
                if max(node_config['iom_slots']) > node_config['max_slots']:
                    raise ValueError(f"Node {node_key} has IOM slots exceeding max_slots")
        
        self.logger.info("Module map validation passed")
        return True
    
    
    def select_io_module(self, io_family, io_type, requires_hart=False, wide_temp_range=False):
        """
        Select IO module based on user inputs and filtering criteria.
        
        Filters IO_Module_Catalog sheet based on:
        - Family (FIO or NIO based on io_family parameter)
        - IO_Type (AI, DI, DO, AO)
        - HART support (optional)
        - Ambient temperature range (optional)
        
        Args:
            io_family (str): 'FIO' or 'NIO' - system family type
            io_type (str): 'AI', 'DI', 'DO', or 'AO' - IO type
            requires_hart (bool): True if HART support required, False otherwise
            wide_temp_range (bool): True if wide temp range required (>60°C), filters to 70°C only
            
        Returns:
            dict: Module information with keys:
                - 'Module': Module name
                - 'Usable_Channels': Maximum usable channels for this configuration
                - 'Family': Module family
                - 'IO_Type': IO type
                - 'Supports_HART': HART support status
                - 'Ambient_Max_C': Maximum ambient temperature
                
        Raises:
            ValueError: If filtering results in 0 or >1 rows
        """
        # Start with full catalog
        filtered_df = self.io_module_catalog_df.copy()
        
        # Step 1: Filter by Family (FIO or NIO)
        if io_family not in ['FIO', 'NIO']:
            raise ValueError(f"Invalid IO family: {io_family}. Must be 'FIO' or 'NIO'")
        
        filtered_df = filtered_df[filtered_df['Family'] == io_family]
        
        if len(filtered_df) == 0:
            raise ValueError(f"No modules found for family: {io_family}")
        
        self.logger.info(f"After family filter ({io_family}): {len(filtered_df)} modules")
        
        # Step 2: Filter by IO_Type
        if io_type not in ['AI', 'DI', 'DO', 'AO', 'SOFT']:
            raise ValueError(f"Invalid IO type: {io_type}. Must be AI, DI, DO, AO, or SOFT")
        
        filtered_df = filtered_df[filtered_df['IO_Type'] == io_type]
        
        if len(filtered_df) == 0:
            raise ValueError(f"No modules found for {io_family} family with IO type {io_type}")
        
        self.logger.info(f"After IO_Type filter ({io_type}): {len(filtered_df)} modules")
        
        # Step 3: Filter by HART support if required
        if requires_hart:
            filtered_df = filtered_df[filtered_df['Supports_HART'] == 'Yes']
            
            if len(filtered_df) == 0:
                raise ValueError(f"No HART-capable modules found for {io_family}/{io_type}")
            
            self.logger.info(f"After HART filter: {len(filtered_df)} modules")
        
        # Step 4: Filter by Ambient temperature
        if wide_temp_range:
            # Keep only rows with 70°C rating for wide temperature range
            filtered_df = filtered_df[filtered_df['Ambient_Max_C'] == 70]
            
            if len(filtered_df) == 0:
                raise ValueError(f"No wide temperature range (70°C) modules found for {io_family}/{io_type}")
            
            self.logger.info(f"After temperature filter (70°C): {len(filtered_df)} modules")
        
        # Step 5: Ensure exactly one module is selected
        if len(filtered_df) > 1:
            # Check if all remaining rows are for the same module (just different configurations)
            unique_modules = filtered_df['Module'].unique()
            
            if len(unique_modules) > 1:
                # Multiple different modules found - this is an error
                error_msg = (
                    f"Multiple different modules found ({len(unique_modules)}: {', '.join(unique_modules)}). "
                    f"Expected exactly 1 module for {io_family}/{io_type}."
                )
                if requires_hart:
                    error_msg += " (HART required)"
                if wide_temp_range:
                    error_msg += " (Wide temp range)"
                
                self.logger.warning(error_msg)
                self.logger.debug(f"Matching modules:\n{filtered_df[['Module', 'IO_Type', 'Supports_HART', 'Ambient_Max_C', 'Usable_Channels']].to_string()}")
                raise ValueError(error_msg)
            else:
                # Same module but different configurations (e.g., Wiring or Signal_Type)
                # Select the one with maximum Usable_Channels
                best_idx = filtered_df['Usable_Channels'].idxmax()
                filtered_df = filtered_df.loc[[best_idx]]
                self.logger.info(f"Multiple configurations found for {unique_modules[0]}. Selected best config (max usable channels)")
        
        # Extract module details
        module_row = filtered_df.iloc[0]
        module_info = {
            'Module': module_row['Module'],
            'Usable_Channels': int(module_row['Usable_Channels']),
            'Family': module_row['Family'],
            'IO_Type': module_row['IO_Type'],
            'Supports_HART': module_row['Supports_HART'],
            'Ambient_Max_C': int(module_row['Ambient_Max_C']),
            'Signal_Type': module_row['Signal_Type'],
            'Nominal_Channels': int(module_row['Nominal_Channels']),
            'Wiring': module_row['Wiring'],
        }
        
        self.logger.info(
            f"Selected module: {module_info['Module']} "
            f"({module_info['IO_Type']}, {module_info['Usable_Channels']} channels, "
            f"Max Temp: {module_info['Ambient_Max_C']}°C, {module_info['Wiring']})"
        )
        
        return module_info
    
    
    def calculate_modules_required(self, signal_counts: Dict[str, int], wired_spares: Dict[str, int], 
                                   selected_modules: Dict[str, dict]) -> Dict[str, dict]:
        """
        Calculate number of modules required for each IO type.
        
        Based on:
        - Total channels needed (signals + wired spares per IO type)
        - Usable channels per selected module
        - Determines module instances needed per IO type
        
        Args:
            signal_counts (Dict[str, int]): Signal count by IO type
                Example: {'AI': 123, 'DI': 270, 'DO': 162}
            wired_spares (Dict[str, int]): Wired spare count by IO type
                Example: {'AI': 25, 'DI': 54, 'DO': 32}
            selected_modules (Dict[str, dict]): Selected module info by IO type
                Example: {
                    'AI': {'Module': 'SAI143-H', 'Usable_Channels': 12, ...},
                    'DI': {'Module': 'SDV144-S', 'Usable_Channels': 12, ...}
                }
        
        Returns:
            Dict[str, dict]: Module requirements per IO type
            {
                'AI': {
                    'signals': 123,
                    'wired_spares': 25,
                    'total_channels_required': 148,
                    'module_name': 'SAI143-H',
                    'usable_channels_per_module': 12,
                    'modules_required': 13,
                    'channels_used': 148,
                    'channels_available': 156,
                    'spare_capacity': 8
                },
                ...
            }
        """
        try:
            module_requirements = {}
            
            io_types_to_process = set(signal_counts.keys()) | set(wired_spares.keys()) | set(selected_modules.keys())
            
            for io_type in io_types_to_process:
                signals = signal_counts.get(io_type, 0)
                spares = wired_spares.get(io_type, 0)
                total_channels = signals + spares
                
                if total_channels == 0:
                    # Skip if no signals and no spares
                    continue
                
                if io_type not in selected_modules:
                    raise ValueError(f"No module selected for {io_type}")
                
                module_info = selected_modules[io_type]
                usable_channels = module_info['Usable_Channels']
                module_name = module_info['Module']
                
                # Calculate modules needed (round up)
                modules_needed = (total_channels + usable_channels - 1) // usable_channels
                
                # Calculate actual channels available
                channels_available = modules_needed * usable_channels
                spare_capacity = channels_available - total_channels
                
                module_requirements[io_type] = {
                    'signals': signals,
                    'wired_spares': spares,
                    'total_channels_required': total_channels,
                    'module_name': module_name,
                    'usable_channels_per_module': usable_channels,
                    'modules_required': modules_needed,
                    'channels_used': total_channels,
                    'channels_available': channels_available,
                    'spare_capacity': spare_capacity,
                    'module_family': module_info['Family'],
                    'signal_type': module_info['Signal_Type'],
                }
                
                self.logger.info(
                    f"Modules required for {io_type}: {modules_needed} x {module_name} "
                    f"({total_channels} channels needed, {channels_available} available)"
                )
            
            return module_requirements
            
        except Exception as e:
            self.logger.error(f"Error calculating modules required: {e}")
            raise
    
    
    def build_mounting_table(self, io_family: str, controller_model: str, 
                            module_requirements: Dict[str, dict]) -> pd.DataFrame:
        """
        Build a mounting table showing module placement in nodes and slots.
        
        Creates a table with:
        - Rows: Node 1 to Node 13 (based on Max_Safety_Nodes)
        - Columns: Slot 1 to Slot 12 (based on standard Yokogawa slots)
        - Content: Module names placed where IOM slots are available
        
        Distributes modules across nodes starting with Node 1, moving to Node 2 when
        Node 1's IOM slots are exhausted, etc.
        
        Args:
            io_family (str): 'FIO' or 'NIO'
            controller_model (str): Controller model name
            module_requirements (Dict[str, dict]): Output from calculate_modules_required()
        
        Returns:
            pd.DataFrame: Mounting table with nodes as rows and slots as columns
                         showing module names where applicable
        """
        try:
            # Get module map and controller limits
            module_map = self.build_module_map(io_family, controller_model)
            max_nodes = module_map['max_nodes']
            
            # Determine max slots from mounting rules
            max_slots = 12  # Standard Yokogawa configuration
            
            # Initialize mounting table with NaN values
            mounting_table = pd.DataFrame(
                [[None for _ in range(max_slots)] for _ in range(max_nodes)],
                index=[f'Node_{i+1}' for i in range(max_nodes)],
                columns=[f'Slot_{i+1}' for i in range(max_slots)]
            )
            
            # Get mounting rules
            mounting_rules = self.mounting_rule_df.copy()
            
            # Track module instances per IO type
            module_instance_count = {io_type: 0 for io_type in module_requirements.keys()}
            
            # Create flat list of (node, slot) pairs in order of available IOM slots
            available_positions = []
            for node_num in range(1, max_nodes + 1):
                # Get IOM slots for this node configuration
                if node_num == 1:
                    # Node 1 uses "Node 1 Only" for single-node, otherwise "Node 1"
                    node_rules = mounting_rules[mounting_rules['Node No'] == 'Node 1 Only']
                    if len(node_rules) == 0:
                        node_rules = mounting_rules[mounting_rules['Node No'] == 1]
                else:
                    # Nodes 2+ use ">1" rules
                    node_rules = mounting_rules[mounting_rules['Node No'] == '>1']
                
                # Get IOM slots for this node configuration (sorted)
                iom_slots = sorted(node_rules[node_rules['Type'] == 'IOM']['Slot'].tolist())
                
                # Add each IOM slot as an available position
                for slot_num in iom_slots:
                    available_positions.append((node_num, slot_num))
            
            # Place modules sequentially in available positions
            position_index = 0
            for io_type in sorted(module_requirements.keys()):
                req = module_requirements[io_type]
                modules_to_place = req['modules_required']
                module_name = req['module_name']
                
                for module_instance in range(modules_to_place):
                    if position_index >= len(available_positions):
                        self.logger.warning(
                            f"Not enough IOM slots for module {module_name}. "
                            f"Need {modules_to_place}, can only place {module_instance}"
                        )
                        break
                    
                    node_num, slot_num = available_positions[position_index]
                    module_instance_count[io_type] += 1
                    
                    # Create module instance label
                    instance_label = f"{module_name}_{module_instance_count[io_type]}"
                    
                    # Place in mounting table
                    mounting_table.loc[f'Node_{node_num}', f'Slot_{slot_num}'] = instance_label
                    position_index += 1
            
            self.logger.info(f"Built mounting table for {controller_model} - placed {position_index} modules")
            return mounting_table
            
        except Exception as e:
            self.logger.error(f"Error building mounting table: {e}")
            raise

