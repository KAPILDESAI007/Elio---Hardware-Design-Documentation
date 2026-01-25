import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows


class DesignInputReview:
    """
    Class to perform Design Input Review for ESD system configuration.
    Reads instrument data, sorts intelligently, assigns modules, and generates output.
    """
    
    def __init__(self, system_type=None, redundancy_types=None, is_types=None, wired_spares=None):
        self.project_dir = Path(r"C:\Working\Others\Python\Cloud App Projects")
        self.df_instruments = None
        self.df_hardware = None
        self.df_fio = None
        self.df_assigned = None
        self.df_unassigned = None
        self.df_wired_spares = None
        
        # User inputs as fallback
        self.system_type = system_type  # ESD, FGS, DCS
        self.redundancy_types = redundancy_types or []  # List of IO types to mark as redundant
        self.is_types = is_types or []  # List of IO types to mark as IS
        self.wired_spares_percentage = wired_spares  # Percentage for wired spares
        
        print(f"[DEBUG] Initialized DesignInputReview with wired_spares_percentage={self.wired_spares_percentage}")
    
    def read_instrument_file(self):
        """Read 3291-36930B-J032-020 RevC_ESD.xls file"""
        print("[DEBUG] Reading instrument file...")
        file_path = self.project_dir / "3291-36930B-J032-020 RevC_ESD.xls"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            self.df_instruments = pd.read_excel(file_path)
            print(f"[DEBUG] Successfully read instrument file with {len(self.df_instruments)} rows")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read instrument file: {e}")
            return False
    
    def extract_required_columns(self):
        """Extract and prepare dataframe with required columns"""
        print("[DEBUG] Extracting required columns...")
        
        if self.df_instruments is None:
            print("[ERROR] Instrument data not loaded")
            return False
        
        required_cols = ['PID_TAG', 'signal_origin', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS']
        
        # Check if all required columns exist
        missing_cols = [col for col in required_cols if col not in self.df_instruments.columns]
        if missing_cols:
            print(f"[WARNING] Missing columns: {missing_cols}")
        
        # Extract available columns
        available_cols = [col for col in required_cols if col in self.df_instruments.columns]
        self.df_instruments = self.df_instruments[available_cols].copy()
        
        # Remove rows with empty PID_TAG
        self.df_instruments = self.df_instruments.dropna(subset=['PID_TAG'])
        self.df_instruments['PID_TAG'] = self.df_instruments['PID_TAG'].astype(str).str.strip()
        
        # Normalize IO_type: convert to uppercase and extract base type
        self.df_instruments['IO_type'] = self.df_instruments['IO_type'].astype(str).str.upper().str.strip()
        self.df_instruments['IO_type_base'] = self.df_instruments['IO_type'].apply(self._extract_io_type_base)
        
        print(f"[DEBUG] Extracted {len(self.df_instruments)} rows with required columns")
        return True
    
    def apply_user_inputs(self):
        """
        Apply user-provided inputs as fallback for missing columns.
        If column exists in file, use it. Otherwise use user input.
        """
        print("[DEBUG] Applying user inputs for missing columns...")
        
        if self.df_instruments is None:
            print("[ERROR] Instrument data not loaded")
            return False
        
        # Handle signal_origin column (fallback to system_type)
        if 'signal_origin' not in self.df_instruments.columns:
            if self.system_type:
                print(f"[DEBUG] signal_origin column missing. Using system_type: {self.system_type}")
                self.df_instruments['signal_origin'] = self.system_type
            else:
                print("[WARNING] signal_origin column missing and no system_type provided")
        
        # Handle IO_REDUNDANCY column (fallback to redundancy_types)
        if 'IO_REDUNDANCY' not in self.df_instruments.columns:
            if self.redundancy_types:
                print(f"[DEBUG] IO_REDUNDANCY column missing. Using redundancy_types: {self.redundancy_types}")
                self.df_instruments['IO_REDUNDANCY'] = self.df_instruments['IO_type_base'].apply(
                    lambda x: 'R' if x in self.redundancy_types else ''
                )
            else:
                print("[WARNING] IO_REDUNDANCY column missing and no redundancy_types provided")
                self.df_instruments['IO_REDUNDANCY'] = ''
        
        # Handle IS_Non_IS column (fallback to is_types)
        if 'IS_Non_IS' not in self.df_instruments.columns:
            if self.is_types:
                print(f"[DEBUG] IS_Non_IS column missing. Using is_types: {self.is_types}")
                self.df_instruments['IS_Non_IS'] = self.df_instruments['IO_type_base'].apply(
                    lambda x: 'IS' if x in self.is_types else 'NIS'
                )
            else:
                print("[WARNING] IS_Non_IS column missing and no is_types provided")
                self.df_instruments['IS_Non_IS'] = 'NIS'
        
        return True
    
    def check_available_columns(self, file_path):
        """
        Check which required columns are available in the input file.
        Returns a dictionary with availability status.
        """
        try:
            df = pd.read_excel(file_path)
            return {
                'has_signal_origin': 'signal_origin' in df.columns,
                'has_io_redundancy': 'IO_REDUNDANCY' in df.columns,
                'has_is_non_is': 'IS_Non_IS' in df.columns
            }
        except Exception as e:
            print(f"[ERROR] Failed to check columns: {e}")
            return {
                'has_signal_origin': False,
                'has_io_redundancy': False,
                'has_is_non_is': False
            }
    
    @staticmethod
    def _extract_io_type_base(io_type_str):
        """
        Extract base IO type (AI, DI, DO, AO) from IO_type string.
        Examples: 'AI-R' -> 'AI', 'DI' -> 'DI', 'AO-2W' -> 'AO'
        """
        io_type_upper = str(io_type_str).upper().strip()
        
        # Look for AI, DI, DO, AO at the start of the string
        base_types = ['AI', 'DI', 'DO', 'AO']
        for base_type in base_types:
            if base_type in io_type_upper:
                # Check if it's at the start or after a delimiter
                match = re.search(r'(AI|DI|DO|AO)', io_type_upper)
                if match:
                    return match.group(1)
        
        # If no match found, return the original string
        return io_type_upper
    
    def sort_by_pid_tag(self):
        """
        Sort instruments by PID_TAG intelligently.
        Groups by prefix, then by numeric/suffix similarity.
        """
        print("[DEBUG] Sorting by PID_TAG...")
        
        if self.df_instruments is None or self.df_instruments.empty:
            print("[ERROR] No instrument data to sort")
            return False
        
        def extract_pid_components(pid):
            """Extract prefix, numbers, and suffix from PID_TAG"""
            match = re.match(r'^([A-Z0-9]+)-([A-Z]+)-(\d+)([A-Z]*)(/\d+)?$', pid)
            if match:
                prefix = match.group(1)  # e.g., "494"
                tag_type = match.group(2)  # e.g., "PIT", "ZPT"
                base_num = int(match.group(3))  # e.g., 115
                suffix = match.group(4)  # e.g., "A", ""
                redundancy = match.group(5) or ""  # e.g., "/06", ""
                return (prefix, tag_type, base_num, suffix, redundancy)
            return (pid, "", 0, "", "")
        
        # Add sorting columns
        self.df_instruments['sort_prefix'] = self.df_instruments['PID_TAG'].apply(
            lambda x: extract_pid_components(x)[0]
        )
        self.df_instruments['sort_type'] = self.df_instruments['PID_TAG'].apply(
            lambda x: extract_pid_components(x)[1]
        )
        self.df_instruments['sort_base_num'] = self.df_instruments['PID_TAG'].apply(
            lambda x: extract_pid_components(x)[2]
        )
        self.df_instruments['sort_suffix'] = self.df_instruments['PID_TAG'].apply(
            lambda x: extract_pid_components(x)[3]
        )
        self.df_instruments['sort_redundancy'] = self.df_instruments['PID_TAG'].apply(
            lambda x: extract_pid_components(x)[4]
        )
        
        # Sort by prefix, type, base number, suffix, redundancy
        self.df_instruments = self.df_instruments.sort_values(
            by=['sort_prefix', 'sort_type', 'sort_base_num', 'sort_suffix', 'sort_redundancy'],
            ignore_index=True
        )
        
        # Drop temporary sorting columns
        self.df_instruments = self.df_instruments.drop(
            columns=['sort_prefix', 'sort_type', 'sort_base_num', 'sort_suffix', 'sort_redundancy']
        )
        
        print(f"[DEBUG] Sorted {len(self.df_instruments)} instruments by PID_TAG")
        return True
    
    def read_hardware_config(self):
        """Read Yokogawa Hardware Conf.xlsx file"""
        print("[DEBUG] Reading hardware configuration...")
        
        file_path = self.project_dir / "Yokogawa Hardware Conf.xlsx"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            self.df_hardware = pd.read_excel(file_path, sheet_name='Hardware Conf')
            # Normalize IO_Type in hardware config
            self.df_hardware['IO_Type'] = self.df_hardware['IO_Type'].astype(str).str.upper().str.strip()
            print(f"[DEBUG] Successfully read hardware config with {len(self.df_hardware)} rows")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read hardware config: {e}")
            return False
    
    def assign_modules(self):
        """
        Assign instruments to modules based on IO_type.
        Each module has a channel capacity and multiple instruments are assigned to same module.
        Uses base IO type (AI, DI, DO, AO) for matching.
        Module_Name in output will be the hardware name (SAI143H, SDV144, etc)
        but instances are tracked internally for slot assignment.
        """
        print("[DEBUG] Assigning instruments to modules...")
        
        if self.df_instruments is None or self.df_hardware is None:
            print("[ERROR] Required data not loaded")
            return False
        
        # Prepare assignment dataframe
        self.df_assigned = self.df_instruments.copy()
        self.df_assigned['Module_Name'] = ""
        self.df_assigned['Module_Instance'] = ""  # Internal tracking: SAI143H_1, SAI143H_2, etc
        self.df_assigned['Channel'] = 0
        self.df_assigned['Node'] = ""
        self.df_assigned['Slot'] = 0
        self.df_assigned['Controller_No'] = ""
        
        # Create mapping from IO_type to Module information
        # Map hardware IO_Type to module info, using base type matching
        # Format: {base_type: {'name': module_name, 'capacity': capacity, 'instances': {instance_num: assigned_count}}}
        module_map = {}
        
        for _, row in self.df_hardware.iterrows():
            io_type = str(row.get('IO_Type', '')).upper().strip()
            module_name = str(row.get('Module Name', '')).strip()
            # Use 'Nos of Channel' column instead of 'Channel_Capacity'
            capacity = int(row.get('Nos of Channel', 16)) if pd.notna(row.get('Nos of Channel')) else 16
            
            if io_type and module_name:
                # Extract base type from hardware IO_Type (e.g., "AI" from "AI")
                base_type = self._extract_io_type_base(io_type)
                
                if base_type not in module_map:
                    module_map[base_type] = {'name': module_name, 'capacity': capacity, 'instances': {}}
                    print(f"[DEBUG] Added module mapping: {base_type} -> {module_name} (capacity: {capacity})")
        
        print(f"[DEBUG] Created module map with {len(module_map)} IO types")
        
        # Assign instruments to modules using base IO type
        # When a module instance is full, create a new instance of the same module
        for idx, row in self.df_assigned.iterrows():
            io_type_base = row.get('IO_type_base', '')
            
            if io_type_base and io_type_base in module_map:
                module_info = module_map[io_type_base]
                base_module_name = module_info['name']
                capacity = module_info['capacity']
                
                # Find or create an instance with available capacity
                instance_num = 1
                while True:
                    # Check if this instance exists
                    if instance_num not in module_info['instances']:
                        module_info['instances'][instance_num] = 0
                    
                    assigned_count = module_info['instances'][instance_num]
                    
                    # If this instance has capacity, use it
                    if assigned_count < capacity:
                        module_info['instances'][instance_num] += 1
                        
                        # Module_Name is always the hardware name (for output)
                        # Module_Instance tracks internal instances (for slot assignment)
                        module_instance = f"{base_module_name}_{instance_num}"
                        
                        channel_num = assigned_count + 1
                        self.df_assigned.at[idx, 'Module_Name'] = base_module_name
                        self.df_assigned.at[idx, 'Module_Instance'] = module_instance
                        self.df_assigned.at[idx, 'Channel'] = channel_num
                        print(f"[DEBUG] Assigned {row['PID_TAG']} to {module_instance} (Module: {base_module_name}), Channel {channel_num}")
                        break
                    else:
                        # This instance is full, try next instance
                        instance_num += 1
            else:
                # IO_type not found in hardware config
                self.df_assigned.at[idx, 'Module_Name'] = ""
                print(f"[DEBUG] No module found for IO_type {row.get('IO_type')} (base: {io_type_base})")
        
        assigned_count = len(self.df_assigned[self.df_assigned['Module_Name'] != ""])
        print(f"[DEBUG] Assigned {assigned_count} instruments to modules")
        return True
    
    def read_fio_config(self):
        """Read FIO sheet from Yokogawa Hardware Conf.xlsx"""
        print("[DEBUG] Reading FIO configuration...")
        
        file_path = self.project_dir / "Yokogawa Hardware Conf.xlsx"
        
        try:
            self.df_fio = pd.read_excel(file_path, sheet_name='FIO')
            print(f"[DEBUG] Successfully read FIO config with {len(self.df_fio)} rows")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read FIO config: {e}")
            return False
    
    def assign_nodes_and_controllers(self):
        """
        Assign Node, Slot and Controller based on FIO configuration.
        Each node has max module slots. Each module occupies one slot.
        When a node is full, move to next node. When all nodes full, create new controller.
        """
        print("[DEBUG] Assigning nodes, slots and controllers...")
        
        if self.df_assigned is None or self.df_fio is None:
            print("[ERROR] Required data not loaded")
            return False
        
        # Create node configuration from FIO sheet
        node_config = {}
        for _, row in self.df_fio.iterrows():
            node_num = int(row.get('Node', 0)) if pd.notna(row.get('Node')) else 0
            # Column is 'No of Module' not 'Max_Modules'
            max_modules = int(row.get('No of Module', 6)) if pd.notna(row.get('No of Module')) else 6
            if node_num > 0:
                node_config[node_num] = {'max_modules': max_modules}
        
        print(f"[DEBUG] Created node config for {len(node_config)} nodes: {node_config}")
        
        # Collect all module instances to assign
        assigned_modules = self.df_assigned[self.df_assigned['Module_Instance'] != ""].copy()
        
        # Get already-assigned instances (Node != 0)
        already_assigned = assigned_modules[(assigned_modules['Node'] != 0) & (assigned_modules['Node'] != '')]
        already_assigned_instances = set(already_assigned['Module_Instance'].unique())
        
        # Get new-to-assign instances (Node == 0 or Node == '')
        to_assign = assigned_modules[(assigned_modules['Node'] == 0) | (assigned_modules['Node'] == '')]
        to_assign_instances = sorted(set(to_assign['Module_Instance'].unique()))
        
        print(f"[DEBUG] Found {len(already_assigned_instances)} already-assigned module instances")
        print(f"[DEBUG] Found {len(to_assign_instances)} module instances to assign")
        
        # Build assignment map for already-assigned instances
        module_assignments = {}
        for module_instance in already_assigned_instances:
            instance_df = already_assigned[already_assigned['Module_Instance'] == module_instance].iloc[0]
            try:
                controller = str(instance_df['Controller_No'])
                node = int(instance_df['Node'])
                slot = int(instance_df['Slot'])
                module_assignments[module_instance] = (controller, node, slot)
            except:
                pass  # Skip rows with invalid data
        
        # Find the last assigned position to continue from
        current_controller = "SCS0101"
        current_node = 1
        current_slot = 1
        
        if module_assignments:
            last_node = max([assignment[1] for assignment in module_assignments.values()])
            nodes_at_last = [assignment for assignment in module_assignments.values() if assignment[1] == last_node]
            last_slot = max([assignment[2] for assignment in nodes_at_last])
            current_node = last_node
            current_slot = last_slot + 1
        
        print(f"[DEBUG] Starting assignment from {current_controller}_N{current_node}S{current_slot}")
        
        # Assign new module instances
        for module_instance in to_assign_instances:
            # Check if current node has capacity
            if current_node not in node_config:
                current_node = 1
                current_controller = f"SCS{int(current_controller[3:]) + 1:04d}"
            
            max_slots = node_config.get(current_node, {}).get('max_modules', 6)
            
            if current_slot <= max_slots:
                module_assignments[module_instance] = (current_controller, current_node, current_slot)
                print(f"[DEBUG] Assigned module instance {module_instance} to {current_controller}_N{current_node}S{current_slot}")
                current_slot += 1
            else:
                # Current node is full, move to next node
                current_node += 1
                current_slot = 1
                
                if current_node > max(node_config.keys()):
                    # Create new controller
                    controller_num = int(current_controller[3:]) + 1
                    current_controller = f"SCS{controller_num:04d}"
                    current_node = 1
                    current_slot = 1
                
                # Assign to new node/slot
                module_assignments[module_instance] = (current_controller, current_node, current_slot)
                print(f"[DEBUG] Assigned module instance {module_instance} to {current_controller}_N{current_node}S{current_slot}")
                current_slot += 1
        
        # Update df_assigned with node/slot/controller assignments
        assigned_count = 0
        for idx, row in self.df_assigned.iterrows():
            if row['Module_Instance'] == "" or pd.isna(row['Module_Instance']):
                continue
            
            module_instance = row['Module_Instance']
            if module_instance in module_assignments:
                controller, node, slot = module_assignments[module_instance]
                self.df_assigned.at[idx, 'Controller_No'] = controller
                self.df_assigned.at[idx, 'Node'] = node
                self.df_assigned.at[idx, 'Slot'] = slot
                assigned_count += 1
        
        print(f"[DEBUG] Assigned {assigned_count} instruments to nodes, slots and controllers")
        return True
    
    def identify_unassigned(self):
        """Identify instruments that could not be assigned"""
        print("[DEBUG] Identifying unassigned instruments...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data")
            return False
        
        self.df_unassigned = self.df_assigned[self.df_assigned['Module_Name'].isna() | (self.df_assigned['Module_Name'] == '')].copy()
        
        print(f"[DEBUG] Found {len(self.df_unassigned)} unassigned instruments")
        if not self.df_unassigned.empty:
            print(f"[DEBUG] Reasons for unassigned: {self.df_unassigned['IO_type'].value_counts().to_dict()}")
        return True
    
    def generate_io_card_summary(self):
        """Generate IO Card Summary with Module names and unique module counts per controller"""
        print("[DEBUG] Generating IO Card Summary...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data to summarize")
            return pd.DataFrame()
        
        # Get assigned instruments only
        assigned_df = self.df_assigned[self.df_assigned['Module_Name'] != ""].copy()
        
        if assigned_df.empty:
            print("[ERROR] No assigned instruments to summarize")
            return pd.DataFrame()
        
        # Group by Module_Name and Controller_No to count UNIQUE modules (not instruments)
        # Each module appears once per controller
        module_controller_df = assigned_df[['Module_Name', 'Controller_No']].drop_duplicates()
        module_controller_counts = module_controller_df.groupby(['Module_Name', 'Controller_No']).size().reset_index(name='Count')
        
        # Get unique modules and controllers
        unique_modules = sorted(module_controller_counts['Module_Name'].unique())
        unique_controllers = sorted(module_controller_counts['Controller_No'].unique())
        
        # Create summary rows
        summary_rows = []
        
        for module in unique_modules:
            row_data = {'Module_Name': module}
            
            # Get count for each controller
            total_qty = 0
            for controller in unique_controllers:
                count = module_controller_counts[
                    (module_controller_counts['Module_Name'] == module) & 
                    (module_controller_counts['Controller_No'] == controller)
                ]['Count'].values
                
                qty = int(count[0]) if len(count) > 0 else 0
                row_data[controller] = qty
                total_qty += qty
            
            row_data['Total_Qty'] = total_qty
            summary_rows.append(row_data)
        
        # Create DataFrame with dynamic columns
        card_summary_df = pd.DataFrame(summary_rows)
        
        print(f"[DEBUG] Generated IO Card Summary with {len(card_summary_df)} modules across {len(unique_controllers)} controllers")
        return card_summary_df
    
    def generate_io_summary(self):
        """Generate IO Summary with SCS No., Signal types, quantities including wired spares"""
        print("[DEBUG] Generating IO Summary...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data to summarize")
            return pd.DataFrame()
        
        # Get assigned instruments only
        assigned_df = self.df_assigned[self.df_assigned['Module_Name'] != ""].copy()
        
        if assigned_df.empty:
            print("[ERROR] No assigned instruments to summarize")
            return pd.DataFrame()
        
        # Create IO type with redundancy info
        def create_io_signal_type(row):
            """Create signal type like AI-R, DI-R, DO, AO-R IS/NIS"""
            io_base = row.get('IO_type_base', '')
            is_flag = str(row.get('IS_Non_IS', '')).strip()
            
            # Check if redundant by looking at IO_type_base
            is_redundant = 'R' in io_base
            
            # Build signal type
            signal_type = io_base
            if is_redundant and not signal_type.endswith('-R'):
                signal_type += '-R'
            
            # Add IS/NIS if available
            if is_flag:
                signal_type += f" {is_flag}"
            
            return signal_type.strip()
        
        assigned_df['Signal_Type'] = assigned_df.apply(create_io_signal_type, axis=1)
        
        # Group by SCS No. and Signal Type to count
        summary_rows = []
        
        for scs in sorted(assigned_df['Controller_No'].unique()):
            scs_data = assigned_df[assigned_df['Controller_No'] == scs]
            
            signal_counts = scs_data['Signal_Type'].value_counts().to_dict()
            
            for signal_type in sorted(signal_counts.keys()):
                count = signal_counts[signal_type]
                
                # Calculate wired spares for this signal type
                wired_spare_count = 0
                if self.wired_spares_percentage is not None and self.wired_spares_percentage > 0:
                    wired_spare_count = int(count * (self.wired_spares_percentage / 100))
                    print(f"[DEBUG] Calculating wired spares for {signal_type}: {count} * {self.wired_spares_percentage}% = {wired_spare_count}")
                
                summary_rows.append({
                    'SCS_No': scs,
                    'Signal_Type': signal_type,
                    'Actual': count,
                    'Wired_Spare': wired_spare_count,
                    'Unwired_Spare': 0,
                    'Total_Qty': count + wired_spare_count
                })
        
        io_summary_df = pd.DataFrame(summary_rows)
        
        print(f"[DEBUG] Generated IO Summary with {len(io_summary_df)} rows")
        return io_summary_df
    
    def generate_wired_spares(self):
        """
        Generate wired spare channels based on user percentage input.
        Spares are distributed evenly across all instances of each module type.
        Creates NEW module instances for spares that don't fit in existing ones.
        Creates spare channel tags like SCS0101_N1S1CH1
        Only generates spares if user explicitly provided wired_spares_percentage > 0
        Validates that total channels (assigned + spares) do not exceed hardware capacity.
        """
        print(f"[DEBUG] Generating wired spare channels... wired_spares_percentage={self.wired_spares_percentage}")
        
        # Only generate spares if user explicitly provided a value
        if self.wired_spares_percentage is None or self.wired_spares_percentage == 0:
            print(f"[DEBUG] No wired spares percentage provided (value={self.wired_spares_percentage}), returning empty dataframe")
            return pd.DataFrame()
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data for spare calculation")
            return pd.DataFrame()
        
        # Get assigned instruments (exclude unassigned)
        assigned_df = self.df_assigned[self.df_assigned['Module_Instance'] != ""].copy()
        
        if assigned_df.empty:
            print(f"[ERROR] No assigned instruments for spare calculation (wired_spares_percentage={self.wired_spares_percentage})")
            return pd.DataFrame()
        
        # Build hardware capacity map: {module_name: capacity}
        hardware_capacity = {}
        if self.df_hardware is not None:
            for _, row in self.df_hardware.iterrows():
                module_name = str(row.get('Module Name', '')).strip()
                capacity = int(row.get('Nos of Channel', 16)) if pd.notna(row.get('Nos of Channel')) else 16
                if module_name:
                    hardware_capacity[module_name] = capacity
        
        spares_data = []
        module_instance_counters = {}  # Track max instance number per module type
        
        # Group by Module_Name to calculate total spares per module type
        for module_name in sorted(assigned_df['Module_Name'].unique()):
            module_df = assigned_df[assigned_df['Module_Name'] == module_name]
            
            # Get hardware capacity for this module
            max_capacity = hardware_capacity.get(module_name, 16)
            
            # Calculate total number of spares for this module type
            total_channels = len(module_df)
            total_spare_count = int(total_channels * (self.wired_spares_percentage / 100))
            
            if total_spare_count > 0:
                # Get all unique module instances for this module type
                module_instances = sorted(module_df['Module_Instance'].unique())
                num_instances = len(module_instances)
                
                # Track the highest instance number for this module type to create new ones later
                max_instance_num = max([int(inst.split('_')[1]) for inst in module_instances])
                module_instance_counters[module_name] = max_instance_num
                
                print(f"[DEBUG] Module {module_name}: {total_channels} actual channels -> {total_spare_count} wired spare channels ({self.wired_spares_percentage}% of {total_channels})")
                print(f"[DEBUG]   Module capacity: {max_capacity} channels per instance")
                print(f"[DEBUG]   Current instances: {num_instances} ({module_instances})")
                
                # Calculate spares for existing instances (fill them up to 16 first)
                spares_placed = 0
                existing_instances_with_spares = []
                
                for module_instance in module_instances:
                    instance_df = module_df[module_df['Module_Instance'] == module_instance]
                    max_channel = int(instance_df['Channel'].max())
                    available_slots = max_capacity - max_channel
                    
                    if available_slots > 0 and spares_placed < total_spare_count:
                        # Add spares to this instance up to capacity
                        spares_for_this_instance = min(available_slots, total_spare_count - spares_placed)
                        
                        # Get node/slot info
                        sample_row = instance_df.iloc[0]
                        controller_no = str(sample_row.get('Controller_No', 'SCS0101'))
                        node_num = int(sample_row.get('Node', 1))
                        slot_num = int(sample_row.get('Slot', 1))
                        
                        # Add spares to this instance
                        for spare_idx in range(1, spares_for_this_instance + 1):
                            spare_channel = max_channel + spare_idx
                            spare_tag = f"{controller_no}_N{node_num}S{slot_num}CH{spare_channel}"
                            
                            spares_data.append({
                                'PID_TAG': spare_tag,
                                'signal_origin': sample_row.get('signal_origin', ''),
                                'IO_type': f"{instance_df['IO_type'].iloc[0]}_Spare",
                                'IO_REDUNDANCY': '',
                                'IS_Non_IS': sample_row.get('IS_Non_IS', 'NIS'),
                                'IO_type_base': instance_df['IO_type_base'].iloc[0],
                                'Module_Name': module_name,
                                'Module_Instance': module_instance,
                                'Channel': spare_channel,
                                'Node': node_num,
                                'Slot': slot_num,
                                'Controller_No': controller_no,
                                'sort_prefix': sample_row.get('sort_prefix', ''),
                                'sort_type': sample_row.get('sort_type', ''),
                                'sort_base_num': sample_row.get('sort_base_num', 0),
                                'sort_suffix': sample_row.get('sort_suffix', ''),
                                'sort_redundancy': sample_row.get('sort_redundancy', '')
                            })
                            spares_placed += 1
                        
                        existing_instances_with_spares.append((module_instance, spares_for_this_instance))
                
                print(f"[DEBUG]   Added {spares_placed} spares to existing instances: {existing_instances_with_spares}")
                
                # If we haven't placed all spares yet, CREATE NEW MODULE INSTANCES
                if spares_placed < total_spare_count:
                    remaining_spares = total_spare_count - spares_placed
                    
                    # Calculate how many new instances we need
                    spares_per_new_instance = max_capacity
                    new_instances_needed = (remaining_spares + spares_per_new_instance - 1) // spares_per_new_instance
                    
                    print(f"[DEBUG]   Need {new_instances_needed} NEW module instances for remaining {remaining_spares} spares")
                    
                    # Get sample row for controller info
                    sample_row = module_df.iloc[0]
                    controller_no = str(sample_row.get('Controller_No', 'SCS0101'))
                    
                    # Create new module instances with spares, will assign Node/Slot later
                    for new_inst_idx in range(new_instances_needed):
                        new_instance_num = max_instance_num + 1 + new_inst_idx
                        new_module_instance = f"{module_name}_{new_instance_num}"
                        
                        # How many spares for this new instance
                        spares_for_new_instance = min(spares_per_new_instance, remaining_spares - (new_inst_idx * spares_per_new_instance))
                        
                        print(f"[DEBUG]     Creating {new_module_instance} with {spares_for_new_instance} spares")
                        
                        # Create spares for this new instance (channels 1 to spares_for_new_instance)
                        for spare_channel in range(1, spares_for_new_instance + 1):
                            # Node/Slot will be assigned later via assign_nodes_and_controllers
                            spare_tag = f"{controller_no}_N0S0CH{spare_channel}"  # Placeholder, will be updated
                            
                            spares_data.append({
                                'PID_TAG': spare_tag,
                                'signal_origin': sample_row.get('signal_origin', ''),
                                'IO_type': f"{module_name.split('_')[0]}_Spare",
                                'IO_REDUNDANCY': '',
                                'IS_Non_IS': sample_row.get('IS_Non_IS', 'NIS'),
                                'IO_type_base': sample_row.get('IO_type_base', module_name),
                                'Module_Name': module_name,
                                'Module_Instance': new_module_instance,
                                'Channel': spare_channel,
                                'Node': 0,  # Will be assigned later
                                'Slot': 0,  # Will be assigned later
                                'Controller_No': controller_no,
                                'sort_prefix': sample_row.get('sort_prefix', ''),
                                'sort_type': sample_row.get('sort_type', ''),
                                'sort_base_num': sample_row.get('sort_base_num', 0),
                                'sort_suffix': sample_row.get('sort_suffix', ''),
                                'sort_redundancy': sample_row.get('sort_redundancy', '')
                            })
                            spares_placed += 1
        
        spares_df = pd.DataFrame(spares_data)
        print(f"[DEBUG] Generated {len(spares_df)} wired spare channels (wired_spares_percentage={self.wired_spares_percentage})")
        print(f"[DEBUG]   Breakdown: {spares_df.groupby('Module_Name').size().to_dict()}")
        return spares_df
    
    def generate_output_file(self):
        """Generate output Excel file with one consolidated Summary sheet and data sheets"""
        print("[DEBUG] Generating output Excel file...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data to write")
            return False
        
        # Create filename with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        output_file = self.project_dir / f"Design Input Review_{today}.xlsx"
        
        # Remove old file if it exists to avoid confusion
        import os
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"[DEBUG] Removed old output file: {output_file}")
            except:
                pass
        
        try:
            # Generate summaries first
            io_card_summary_df = self.generate_io_card_summary()
            io_summary_df = self.generate_io_summary()
            
            # Prepare assigned data with correct column order
            assigned_df = self.df_assigned[self.df_assigned['Module_Name'] != ""].copy()
            # Remove internal tracking columns
            assigned_df = assigned_df.drop(columns=['IO_type_base', 'Module_Instance'], errors='ignore')
            
            # Regenerate PID_TAG for wired spares (those with N0S0 placeholders)
            # These are spares that were assigned to new nodes/slots after generation
            print(f"[DEBUG] Before tag regen: assigned_df has {len(assigned_df)} rows")
            print(f"[DEBUG] Sample PID_TAGs before regen: {assigned_df['PID_TAG'].iloc[:5].tolist()}")
            print(f"[DEBUG] Sample PID_TAGs at end before regen: {assigned_df['PID_TAG'].iloc[-5:].tolist()}")
            
            mask_placeholder_tags = assigned_df['PID_TAG'].str.contains('SCS.*_N0S0CH', regex=True, na=False)
            print(f"[DEBUG] Rows matching N0S0 pattern: {mask_placeholder_tags.sum()}")
            print(f"[DEBUG] Rows with N0S0 that will be regenerated: {assigned_df[mask_placeholder_tags]['PID_TAG'].tolist()[:10]}")
            
            if mask_placeholder_tags.any():
                count_updated = 0
                for idx in assigned_df[mask_placeholder_tags].index:
                    try:
                        controller = str(assigned_df.at[idx, 'Controller_No'])
                        # Convert to int, handling potential issues
                        node_val = assigned_df.at[idx, 'Node']
                        slot_val = assigned_df.at[idx, 'Slot']
                        channel_val = assigned_df.at[idx, 'Channel']
                        
                        # Ensure they are integers
                        node = int(node_val) if pd.notna(node_val) else 0
                        slot = int(slot_val) if pd.notna(slot_val) else 0
                        channel = int(channel_val) if pd.notna(channel_val) else 0
                        
                        if node > 0 and slot > 0 and channel > 0:
                            new_tag = f"{controller}_N{node}S{slot}CH{channel}"
                            assigned_df.at[idx, 'PID_TAG'] = new_tag
                            count_updated += 1
                            if count_updated <= 5:
                                print(f"[DEBUG]   Row {idx}: Updated to {new_tag} (Node={node}, Slot={slot}, Channel={channel})")
                    except Exception as e:
                        print(f"[WARNING] Could not update tag for row {idx}: {e}")
                        pass
                print(f"[DEBUG] Updated {count_updated} wired spare tags from N0S0 placeholders to proper format")
            
            print(f"[DEBUG] After tag regen: assigned_df has {len(assigned_df)} rows")
            print(f"[DEBUG] Sample PID_TAGs after regen: {assigned_df['PID_TAG'].iloc[:5].tolist()}")
            print(f"[DEBUG] Sample PID_TAGs at end after regen: {assigned_df['PID_TAG'].iloc[-5:].tolist()}")
            
            # Filter out pre-existing placeholder spares (lowercase check for "spare" in PID_TAG)
            # These are the SPARE1-SPARE92 rows from input, NOT the generated wired spares
            before_filter = len(assigned_df)
            print(f"[DEBUG] Before filtering placeholder spares: {before_filter} rows")
            print(f"[DEBUG] Rows with 'spare' (lowercase) in PID_TAG: {assigned_df['PID_TAG'].str.lower().str.contains('spare', na=False).sum()}")
            print(f"[DEBUG] Sample rows with 'spare': {assigned_df[assigned_df['PID_TAG'].str.lower().str.contains('spare', na=False)]['PID_TAG'].head(10).tolist()}")
            
            assigned_df = assigned_df[~assigned_df['PID_TAG'].str.lower().str.contains('spare', na=False)]
            filtered_out = before_filter - len(assigned_df)
            print(f"[DEBUG] After filtering: {len(assigned_df)} rows (filtered out {filtered_out})")
            if filtered_out > 0:
                print(f"[DEBUG] Filtered out {filtered_out} pre-existing placeholder spares")
            
            # Reorder columns: Controller_No, Node, Slot, Channel, and rest
            col_order = ['PID_TAG', 'signal_origin', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS', 
                         'Module_Name', 'Controller_No', 'Node', 'Slot', 'Channel']
            available_cols = [col for col in col_order if col in assigned_df.columns]
            remaining_cols = [col for col in assigned_df.columns if col not in col_order]
            final_cols = available_cols + remaining_cols
            assigned_df = assigned_df[final_cols]
            
            # Count wired spares before writing
            wired_spares_count = len(assigned_df[assigned_df['PID_TAG'].str.contains('SCS0101_N', na=False)])
            print(f"[DEBUG] Before Excel write - Total rows: {len(assigned_df)}, Wired spares: {wired_spares_count}")
            print(f"[DEBUG] Wired spare samples: {assigned_df[assigned_df['PID_TAG'].str.contains('SCS0101_N', na=False)]['PID_TAG'].head(10).tolist()}")
            
            # Show ALL rows with SCS0101_N pattern before writing
            wired_before = assigned_df[assigned_df['PID_TAG'].str.contains('SCS0101_N', na=False)]
            print(f"[DEBUG] All {len(wired_before)} wired spares before write:")
            print(wired_before[['PID_TAG', 'Module_Name', 'Node', 'Slot', 'Channel']].to_string())
            
            # Use pandas ExcelWriter - more reliable than openpyxl dataframe_to_rows
            print(f"[DEBUG] Writing to Excel file: {output_file}")
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Write Assigned sheet
                print(f"[DEBUG] Writing {len(assigned_df)} rows to 'Assigned' sheet...")
                assigned_df.to_excel(writer, sheet_name='Assigned', index=False)
                print(f"[DEBUG] Assigned sheet written successfully")
                
                # Write Unassigned sheet
                if self.df_unassigned is not None and not self.df_unassigned.empty:
                    unassigned_df = self.df_unassigned.drop(columns=['IO_type_base', 'Module_Instance'], errors='ignore')
                    print(f"[DEBUG] Writing {len(unassigned_df)} rows to 'Unassigned' sheet...")
                    unassigned_df.to_excel(writer, sheet_name='Unassigned', index=False)
                    print(f"[DEBUG] Unassigned sheet written successfully")
            
            # ExcelWriter context closed - file is saved
            print(f"[DEBUG] ExcelWriter closed and data sheets saved")
            
            # Now add Summary sheet by reopening the file with openpyxl
            from openpyxl import load_workbook
            print(f"[DEBUG] Adding Summary sheet...")
            wb = load_workbook(output_file)
            ws_summary = wb.create_sheet('Summary')
            
            current_row = 1
            assigned_count = len(assigned_df)
            unassigned_count = len(self.df_unassigned) if self.df_unassigned is not None else 0
            
            # SECTION A: Signal Summary
            ws_summary[f'A{current_row}'] = 'SIGNAL SUMMARY'
            current_row += 1
            
            ws_summary[f'A{current_row}'] = 'Status'
            ws_summary[f'B{current_row}'] = 'Count'
            current_row += 1
            
            ws_summary[f'A{current_row}'] = 'Assigned'
            ws_summary[f'B{current_row}'] = assigned_count
            current_row += 1
            
            ws_summary[f'A{current_row}'] = 'Unassigned'
            ws_summary[f'B{current_row}'] = unassigned_count
            current_row += 1
            
            current_row += 2  # 2 rows gap
            
            # SECTION B: IO Card Summary
            ws_summary[f'A{current_row}'] = 'IO CARD SUMMARY'
            current_row += 1
            
            if not io_card_summary_df.empty:
                for col_idx, col_name in enumerate(io_card_summary_df.columns, 1):
                    ws_summary.cell(row=current_row, column=col_idx, value=col_name)
                current_row += 1
                
                for row_idx, (_, row_data) in enumerate(io_card_summary_df.iterrows(), 1):
                    for col_idx, value in enumerate(row_data.values, 1):
                        ws_summary.cell(row=current_row + row_idx - 1, column=col_idx, value=value)
                
                current_row += len(io_card_summary_df) + 1
            else:
                ws_summary[f'A{current_row}'] = 'No IO Card data'
                current_row += 1
            
            current_row += 1  # 1 blank row for spacing
            
            # SECTION C: IO Channel Summary
            ws_summary[f'A{current_row}'] = 'IO CHANNEL SUMMARY'
            current_row += 1
            
            if not io_summary_df.empty:
                for col_idx, col_name in enumerate(io_summary_df.columns, 1):
                    ws_summary.cell(row=current_row, column=col_idx, value=col_name)
                current_row += 1
                
                for row_idx, (_, row_data) in enumerate(io_summary_df.iterrows(), 1):
                    for col_idx, value in enumerate(row_data.values, 1):
                        ws_summary.cell(row=current_row + row_idx - 1, column=col_idx, value=value)
            else:
                ws_summary[f'A{current_row}'] = 'No IO Summary data'
            
            # Save the workbook with Summary sheet
            print(f"[DEBUG] Saving workbook with Summary sheet...")
            wb.save(output_file)
            print(f"[DEBUG] Workbook saved with all sheets")
            print(f"[DEBUG] Created consolidated Summary sheet with three sections")
            
            # Verify file was written and check content
            import os
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"[DEBUG] File saved successfully, size: {file_size} bytes")
                
                # Re-read the file to verify wired spares are there
                try:
                    verify_df = pd.read_excel(output_file, sheet_name='Assigned')
                    verify_wired = verify_df[verify_df['PID_TAG'].str.contains('SCS0101_N', na=False)]
                    print(f"[DEBUG] VERIFICATION: Excel file has {len(verify_df)} total rows")
                    print(f"[DEBUG] VERIFICATION: Found {len(verify_wired)} wired spares in Excel file")
                    if len(verify_wired) > 0:
                        print(f"[DEBUG] VERIFICATION: Sample wired spares from Excel:")
                        print(verify_wired[['PID_TAG', 'Module_Name', 'Node', 'Slot', 'Channel']].head(20).to_string())
                    else:
                        print(f"[WARNING] No wired spares found in Excel file!")
                        print(f"[DEBUG] All PID_TAGs in Excel file:")
                        print(verify_df[['PID_TAG', 'Module_Name']].head(20).to_string())
                        print(f"[DEBUG] Tail of Excel file:")
                        print(verify_df[['PID_TAG', 'Module_Name']].tail(20).to_string())
                except Exception as ve:
                    print(f"[WARNING] Could not verify file: {ve}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[ERROR] File was not created!")
            
            print(f"[SUCCESS] Output file created: {output_file}")
            
            return True
        
        except Exception as e:
            print(f"[ERROR] Failed to generate output file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_complete_review(self):
        """Execute complete design input review process"""
        print("="*60)
        print("Starting Design Input Review Process")
        print("="*60)
        
        steps = [
            ("Reading instrument file", self.read_instrument_file),
            ("Extracting required columns", self.extract_required_columns),
            ("Applying user inputs for missing columns", self.apply_user_inputs),
            ("Sorting by PID_TAG", self.sort_by_pid_tag),
            ("Reading hardware configuration", self.read_hardware_config),
            ("Assigning modules", self.assign_modules),
            ("Reading FIO configuration", self.read_fio_config),
            ("Assigning nodes and controllers", self.assign_nodes_and_controllers),
            ("Identifying unassigned instruments", self.identify_unassigned),
        ]
        
        for step_name, step_func in steps:
            print(f"\n[STEP] {step_name}...")
            if not step_func():
                print(f"[ERROR] Failed at step: {step_name}")
                return False
        
        # Generate wired spares (optional, always succeeds)
        print(f"\n[STEP] Generating wired spares...")
        self.df_wired_spares = self.generate_wired_spares()
        
        # If wired spares were generated, add them to df_assigned and reassign nodes/slots
        if self.df_wired_spares is not None and not self.df_wired_spares.empty:
            print(f"[STEP] Adding wired spares to assigned data...")
            self.df_assigned = pd.concat([self.df_assigned, self.df_wired_spares], ignore_index=True)
            print(f"[DEBUG] df_assigned now has {len(self.df_assigned)} rows (assigned + spares)")
            
            print(f"[STEP] Reassigning nodes and controllers for new spare module instances...")
            if not self.assign_nodes_and_controllers():
                print(f"[ERROR] Failed to reassign nodes and controllers for spare instances")
                return False
        
        # Generate output file
        print(f"\n[STEP] Generating output file...")
        if not self.generate_output_file():
            print(f"[ERROR] Failed to generate output file")
            return False
        
        print("\n" + "="*60)
        print("Design Input Review Process Completed Successfully!")
        print("="*60)
        return True


if __name__ == "__main__":
    reviewer = DesignInputReview()
    reviewer.run_complete_review()
