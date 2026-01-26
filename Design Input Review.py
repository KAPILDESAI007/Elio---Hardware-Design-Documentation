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
    
    def __init__(self, system_type=None, controller_model=None, explosion_protection=None, 
                 temperature_rating=None, redundancy_types=None, is_types=None, wired_spares=None):
        self.project_dir = Path(r"C:\Working\Others\Python\Cloud App Projects")
        self.df_instruments = None
        self.df_hardware = None
        self.df_fio = None
        self.df_controller_limits = None
        self.df_mounting_rule = None
        self.df_assigned = None
        self.df_unassigned = None
        self.df_wired_spares = None
        
        # Controller constraints
        self.controller_constraints = {}  # Will store max nodes, modules, etc
        
        # User inputs as fallback
        self.system_type = system_type  # ESD, FGS, DCS
        self.controller_model = controller_model  # Controller model selection
        self.explosion_protection = explosion_protection  # Yes/No
        self.temperature_rating = temperature_rating  # Standard/Wide
        self.redundancy_types = redundancy_types or []  # List of IO types to mark as redundant
        self.is_types = is_types or []  # List of IO types to mark as IS
        self.wired_spares_percentage = wired_spares  # Percentage for wired spares
        
        print(f"[DEBUG] Initialized DesignInputReview with:")
        print(f"  system_type={self.system_type}")
        print(f"  controller_model={self.controller_model}")
        print(f"  explosion_protection={self.explosion_protection}")
        print(f"  temperature_rating={self.temperature_rating}")
        print(f"  wired_spares_percentage={self.wired_spares_percentage}")
    
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
        
        # Handle Controller_Model column (fallback to controller_model user input)
        if 'Controller_Model' not in self.df_instruments.columns:
            if self.controller_model:
                print(f"[DEBUG] Controller_Model column missing. Using controller_model: {self.controller_model}")
                self.df_instruments['Controller_Model'] = self.controller_model
            else:
                print("[WARNING] Controller_Model column missing and no controller_model provided")
        
        # Apply Controller_Model to map System_Type for ESD and FGS (should be mapped to Safety)
        if self.read_controller_limits():
            self.df_instruments = self.map_system_type_from_controller()
        
        return True
    
    def read_controller_limits(self):
        """Read Controller_Limits sheet from Yokogawa_SIS_Constraints_Model_v3.xlsx"""
        print("[DEBUG] Reading Controller_Limits configuration...")
        
        file_path = self.project_dir / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            self.df_controller_limits = pd.read_excel(file_path, sheet_name='Controller_Limits')
            print(f"[DEBUG] Successfully read Controller_Limits with {len(self.df_controller_limits)} rows")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read Controller_Limits: {e}")
            return False
    
    def map_system_type_from_controller(self):
        """
        Map System_Type based on Controller_Model from Controller_Limits sheet.
        ESD and FGS should be mapped to Safety as System_Type.
        """
        print("[DEBUG] Mapping System_Type from Controller_Model...")
        
        if self.df_controller_limits is None or self.df_instruments is None:
            print("[WARNING] Controller_Limits or instruments data not available")
            return self.df_instruments
        
        # Create a mapping from Controller_Model to System_Type
        controller_mapping = dict(zip(
            self.df_controller_limits['Controller_Model'],
            self.df_controller_limits['System_Type']
        ))
        
        print(f"[DEBUG] Controller_Model to System_Type mapping: {controller_mapping}")
        
        # Apply mapping if Controller_Model exists in instruments
        if 'Controller_Model' in self.df_instruments.columns:
            def map_system_type(row):
                controller = row.get('Controller_Model', '')
                if pd.isna(controller) or controller == '':
                    return row.get('signal_origin', '')
                
                # Map controller to system type
                if controller in controller_mapping:
                    mapped_type = controller_mapping[controller]
                    # Override ESD and FGS to Safety
                    if row.get('signal_origin') in ['ESD', 'FGS']:
                        return 'Safety'
                    return mapped_type
                return row.get('signal_origin', '')
            
            self.df_instruments['signal_origin'] = self.df_instruments.apply(map_system_type, axis=1)
            print(f"[DEBUG] Mapped System_Type from Controller_Model")
        
        return self.df_instruments
    
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
                'has_is_non_is': 'IS_Non_IS' in df.columns,
                'has_controller_model': 'Controller_Model' in df.columns
            }
        except Exception as e:
            print(f"[ERROR] Failed to check columns: {e}")
            return {
                'has_signal_origin': False,
                'has_io_redundancy': False,
                'has_is_non_is': False,
                'has_controller_model': False
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
        """Read Yokogawa_SIS_Constraints_Model_v3.xlsx file from templates folder"""
        print("[DEBUG] Reading hardware configuration...")
        
        file_path = self.project_dir / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            # Read IO_Module_Catalog sheet
            self.df_hardware = pd.read_excel(file_path, sheet_name='IO_Module_Catalog')
            
            # Filter for FIO family modules only
            self.df_hardware = self.df_hardware[self.df_hardware['Family'] == 'FIO'].copy()
            
            # Drop duplicate module/IO_Type combinations (keep first occurrence)
            self.df_hardware = self.df_hardware.drop_duplicates(subset=['Module', 'IO_Type'], keep='first')
            
            # Normalize IO_Type in hardware config
            self.df_hardware['IO_Type'] = self.df_hardware['IO_Type'].astype(str).str.upper().str.strip()
            
            # Create a standard 'Nos of Channel' column if it doesn't exist (use Nominal_Channels)
            if 'Nos of Channel' not in self.df_hardware.columns:
                self.df_hardware['Nos of Channel'] = self.df_hardware['Nominal_Channels']
            
            # Create a 'Module Name' column from 'Module' if it doesn't exist
            if 'Module Name' not in self.df_hardware.columns:
                self.df_hardware['Module Name'] = self.df_hardware['Module']
            
            print(f"[DEBUG] Successfully read hardware config with {len(self.df_hardware)} rows")
            print(f"[DEBUG] Hardware config columns: {list(self.df_hardware.columns)}")
            print(f"[DEBUG] Sample modules: {self.df_hardware[['Module', 'IO_Type', 'Nos of Channel']].drop_duplicates().head(10).to_string()}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read hardware config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def assign_modules(self):
        """
        Assign instruments to modules with comprehensive constraints:
        1. Redundancy: For redundant signals, use odd channels (1,3,5,7...) and leave even channels empty (2,4,6,8...)
        2. IS/NIS: All {IO_Type}-IS in one module, all {IO_Type}-NIS in separate module
        3. HART: Filter based on Supports_HART
        4. Temperature: Adjust capacity based on ambient_Max_C and temperature_rating
        5. Slots fill sequentially, regardless of redundancy
        """
        print("[DEBUG] Assigning instruments to modules with comprehensive constraints...")
        
        if self.df_instruments is None or self.df_hardware is None:
            print("[ERROR] Required data not loaded")
            return False
        
        # Prepare assignment dataframe
        self.df_assigned = self.df_instruments.copy()
        self.df_assigned['Module_Name'] = ""
        self.df_assigned['Module_Instance'] = ""
        self.df_assigned['Channel'] = 0
        self.df_assigned['Node'] = ""
        self.df_assigned['Slot'] = 0
        self.df_assigned['Controller_No'] = ""
        self.df_assigned['Redundancy_Flag'] = ""
        
        # Create mapping from (IO_type, IS_type) to Module information
        # Format: {(base_type, is_type): [{'name': module_name, 'capacity': capacity, 'is_hart': bool, 'instances': {}}]}
        # This ensures all AI-IS are together, all AI-NIS are together, etc.
        module_map = {}
        
        unique_modules = self.df_hardware.drop_duplicates(subset=['Module', 'IO_Type'])
        print(f"[DEBUG] Processing {len(unique_modules)} unique modules for assignment")
        
        for _, row in unique_modules.iterrows():
            io_type = str(row.get('IO_Type', '')).upper().strip()
            module_name = str(row.get('Module', '')).strip()
            nominal_capacity = int(row.get('Nominal_Channels', 16)) if pd.notna(row.get('Nominal_Channels')) else 16
            usable_capacity = int(row.get('Usable_Channels', 16)) if pd.notna(row.get('Usable_Channels')) else nominal_capacity
            supports_hart = str(row.get('Supports_HART', '')).strip().lower() == 'yes'
            ambient_max = float(row.get('Ambient_Max_C', 60)) if pd.notna(row.get('Ambient_Max_C')) else 60
            
            # Adjust capacity based on temperature rating
            if self.temperature_rating == 'Wide' and ambient_max < 70:
                capacity = int(usable_capacity * 0.8)
            else:
                capacity = usable_capacity
            
            if io_type and module_name:
                base_type = self._extract_io_type_base(io_type)
                # Normalize base_type: DI-RL, DI-R all become DI; DO-R becomes DO, etc.
                base_type_normalized = base_type.split('-')[0]  # Take only first part before dash
                
                if base_type_normalized not in module_map:
                    module_map[base_type_normalized] = []
                
                module_map[base_type_normalized].append({
                    'name': module_name,
                    'capacity': capacity,
                    'is_hart': supports_hart,
                    'instances': {}  # {instance_num: {is_count, nis_count, channels_used, is_redundant}}
                })
                print(f"[DEBUG] Added module: {base_type_normalized} -> {module_name} (capacity: {capacity}, HART: {supports_hart})")
        
        print(f"[DEBUG] Created module map with {sum(len(v) for v in module_map.values())} modules across {len(module_map)} IO types")
        
        # Sort instruments by IO type and IS/NIS to group them together
        # This helps ensure all AI-IS go together, all AI-NIS go together, etc.
        self.df_assigned['sort_key'] = (
            self.df_assigned['IO_type_base'].astype(str) + '_' +
            self.df_assigned['IS_Non_IS'].astype(str)
        )
        
        # Assign instruments to modules
        unassigned_count = 0
        for idx, row in self.df_assigned.iterrows():
            io_type_base = row.get('IO_type_base', '')
            # Normalize io_type_base: DI-RL, DI-R → DI; DO-R → DO, etc.
            io_type_base_normalized = io_type_base.split('-')[0] if io_type_base else ''
            
            is_type = row.get('IS_Non_IS', 'NIS')
            pid_tag = row.get('PID_TAG', 'UNKNOWN')
            is_redundant = str(row.get('IO_REDUNDANCY', '')).strip() in ['R', 'r', 'Y', 'y', 'Yes', 'YES', 'yes']
            signal_type = row.get('signal_origin', '')
            
            # Check if signal requires HART
            signal_requires_hart = signal_type in ['HART', 'hart'] or 'HART' in str(row.get('IO_type', ''))
            
            if io_type_base_normalized and io_type_base_normalized in module_map:
                assigned = False
                
                # Try each available module for this IO type
                for module_info in module_map[io_type_base_normalized]:
                    # Skip HART modules if signal doesn't need HART, or vice versa
                    if signal_requires_hart and not module_info['is_hart']:
                        continue
                    if not signal_requires_hart and module_info['is_hart']:
                        continue
                    
                    base_module_name = module_info['name']
                    capacity = module_info['capacity']
                    
                    # Find or create an instance with available capacity
                    instance_num = 1
                    while instance_num <= 10:  # Safety limit
                        if instance_num not in module_info['instances']:
                            module_info['instances'][instance_num] = {
                                'IS_count': 0,
                                'NIS_count': 0,
                                'channels_per_slot': [0] * 8,  # Track channels used per slot (0-7 for max 8 slots)
                                'is_type': None  # Track which type (IS/NIS) this instance contains
                            }
                        
                        instance_data = module_info['instances'][instance_num]
                        
                        # Check if this instance can accept more signals
                        # IS and NIS cannot mix
                        instance_is_type = instance_data['is_type']
                        if instance_is_type is None:
                            # First signal in this instance
                            instance_data['is_type'] = is_type
                            instance_is_type = is_type
                        
                        # Can only add if same IS/NIS type
                        if instance_is_type != is_type:
                            instance_num += 1
                            continue
                        
                        # Try to find an available slot with available channels
                        assigned_to_slot = False
                        for slot_idx in range(8):  # Max 8 slots
                            channels_used = instance_data['channels_per_slot'][slot_idx]
                            
                            if is_redundant:
                                # For redundant signals: use odd channels only (1, 3, 5, 7, 9, 11, 13, 15)
                                # Odd channels are at indices 0, 2, 4, 6, 8, 10, 12, 14 if we count 1-based
                                # So for slot with channels_used on it, figure out next odd channel
                                odd_channels = [1, 3, 5, 7, 9, 11, 13, 15]
                                
                                # Count how many odd channels are available in this slot
                                # If channels_used = 0, next odd channel is 1
                                # If channels_used = 1, next odd channel is 3 (skip even channel 2)
                                # If channels_used = 2, next odd channel is 5 (skip even channel 4), etc.
                                next_odd_idx = channels_used  # This gives us the index of the next odd channel
                                
                                if next_odd_idx < len(odd_channels):
                                    next_channel = odd_channels[next_odd_idx]
                                    if next_channel <= capacity:
                                        instance_data['channels_per_slot'][slot_idx] = channels_used + 1
                                        if is_type == 'IS':
                                            instance_data['IS_count'] += 1
                                        else:
                                            instance_data['NIS_count'] += 1
                                        
                                        module_instance = f"{base_module_name}_{instance_num}"
                                        
                                        self.df_assigned.at[idx, 'Module_Name'] = base_module_name
                                        self.df_assigned.at[idx, 'Module_Instance'] = module_instance
                                        self.df_assigned.at[idx, 'Channel'] = next_channel
                                        self.df_assigned.at[idx, 'Redundancy_Flag'] = 'Yes'
                                        
                                        print(f"[DEBUG] [ASSIGNED] {pid_tag} (redundant, IS/NIS={is_type}) to {module_instance}, Slot {slot_idx + 1}, Channel {next_channel}")
                                        assigned = True
                                        assigned_to_slot = True
                                        break
                            else:
                                # Non-redundant: use any available channel sequentially (1, 2, 3, 4, ...)
                                if channels_used < capacity:
                                    next_channel = channels_used + 1
                                    instance_data['channels_per_slot'][slot_idx] = channels_used + 1
                                    if is_type == 'IS':
                                        instance_data['IS_count'] += 1
                                    else:
                                        instance_data['NIS_count'] += 1
                                    
                                    module_instance = f"{base_module_name}_{instance_num}"
                                    
                                    self.df_assigned.at[idx, 'Module_Name'] = base_module_name
                                    self.df_assigned.at[idx, 'Module_Instance'] = module_instance
                                    self.df_assigned.at[idx, 'Channel'] = next_channel
                                    self.df_assigned.at[idx, 'Redundancy_Flag'] = 'No'
                                    
                                    print(f"[DEBUG] [ASSIGNED] {pid_tag} (non-redundant, IS/NIS={is_type}) to {module_instance}, Slot {slot_idx + 1}, Channel {next_channel}")
                                    assigned = True
                                    assigned_to_slot = True
                                    break
                        
                        if assigned_to_slot:
                            break
                        else:
                            instance_num += 1
                    
                    if assigned:
                        break
                
                if not assigned:
                    print(f"[WARNING] [UNASSIGNED] {pid_tag} ({is_type}) - couldn't find compatible module")
                    unassigned_count += 1
            else:
                print(f"[WARNING] [UNASSIGNED] {pid_tag} - IO_type {io_type_base} not available")
                unassigned_count += 1
        
        assigned_count = len(self.df_assigned[self.df_assigned['Module_Name'] != ""])
        print(f"[DEBUG] Module assignment complete: {assigned_count} assigned, {unassigned_count} unassigned")
        return True
    
    def _get_usable_channels_factor(self):
        """
        Get usable channels factor based on temperature rating.
        Standard: 100% (0-60°C)
        Wide: Reduced for high ambient (40-70°C)
        """
        if self.temperature_rating == 'Wide':
            return 0.8  # Wide temperature modules have 80% usable channels
        return 1.0  # Standard temperature modules have 100% usable channels
    
    def read_fio_config(self):
        """Read FIO sheet from Yokogawa_SIS_Constraints_Model_v3.xlsx or fallback to old file"""
        print("[DEBUG] Reading FIO configuration...")
        
        # Try new file first
        file_path = self.project_dir / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        try:
            self.df_fio = pd.read_excel(file_path, sheet_name='FIO')
            print(f"[DEBUG] Successfully read FIO config with {len(self.df_fio)} rows")
            return True
        except Exception as e:
            print(f"[WARNING] Failed to read FIO from new file: {e}")
            # Fallback to old file if available
            old_file_path = self.project_dir / "templates" / "Yokogawa Hardware Conf.xlsx"
            try:
                self.df_fio = pd.read_excel(old_file_path, sheet_name='FIO')
                print(f"[DEBUG] Successfully read FIO config from old file with {len(self.df_fio)} rows")
                return True
            except Exception as e2:
                print(f"[ERROR] Failed to read FIO config from both files: {e2}")
                return False
    
    def read_mounting_rule(self):
        """Read Mounting Rule sheet from Yokogawa_SIS_Constraints_Model_v3.xlsx"""
        print("[DEBUG] Reading Mounting Rule configuration...")
        
        file_path = self.project_dir / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            self.df_mounting_rule = pd.read_excel(file_path, sheet_name='Mounting Rule')
            print(f"[DEBUG] Successfully read Mounting Rule with {len(self.df_mounting_rule)} rows")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read Mounting Rule: {e}")
            return False
    
    def read_controller_limits(self):
        """Read Controller_Limits sheet and extract constraints for selected controller model"""
        print("[DEBUG] Reading Controller_Limits configuration...")
        
        file_path = self.project_dir / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return False
        
        try:
            self.df_controller_limits = pd.read_excel(file_path, sheet_name='Controller_Limits')
            print(f"[DEBUG] Successfully read Controller_Limits with {len(self.df_controller_limits)} rows")
            
            # Extract constraints for the selected controller model
            if self.controller_model:
                controller_row = self.df_controller_limits[
                    self.df_controller_limits['Controller_Model'] == self.controller_model
                ]
                if not controller_row.empty:
                    self.controller_constraints = {
                        'Max_Safety_Nodes': int(controller_row['Max_Safety_Nodes'].iloc[0]),
                        'Max_FIO_Modules': int(controller_row['Max_FIO_Modules'].iloc[0]),
                        'Max_Dual_Red_Modules': int(controller_row['Max_Dual_Red_Modules'].iloc[0])
                    }
                    print(f"[DEBUG] Controller constraints: {self.controller_constraints}")
                else:
                    print(f"[WARNING] Controller model {self.controller_model} not found in limits")
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to read Controller_Limits: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_mounting_type_for_nodes(self, num_nodes):
        """
        Determine mounting type based on number of nodes.
        If only one node: SCU_Without_ESB
        If more than one node: SCU_With_ESB for Node-1, SNU for Node-2+
        """
        if num_nodes == 1:
            return {1: 'SCU_Without_ESB'}
        elif num_nodes > 1:
            return {1: 'SCU_With_ESB', **{i: 'SNU' for i in range(2, num_nodes + 1)}}
        return {}
    
    def get_available_slots_for_node(self, node_num, mounting_type):
        """
        Get available IOM slots for a given node based on mounting type.
        Returns list of slot numbers where Type is 'IOM'.
        """
        if self.df_mounting_rule is None:
            print(f"[WARNING] Mounting rule not loaded, using default slots")
            # Default: Node 1 has 6 slots, Node 2+ has 8 slots
            if node_num == 1:
                return list(range(1, 7))
            else:
                return list(range(1, 9))
        
        rule_df = self.df_mounting_rule[
            (self.df_mounting_rule['Node Type'] == mounting_type) &
            (self.df_mounting_rule['Type'] == 'IOM')
        ]
        
        slots = sorted(rule_df['Slot'].unique().tolist())
        print(f"[DEBUG] Available IOM slots for {mounting_type} (Node-{node_num}): {slots}")
        return slots
    
    def validate_controller_constraints(self, num_nodes, num_fio_modules, num_dual_red_modules):
        """
        Validate that assignment doesn't exceed controller limits.
        Returns (is_valid, error_message)
        """
        if not self.controller_constraints:
            print("[WARNING] No controller constraints loaded, skipping validation")
            return True, ""
        
        constraints = self.controller_constraints
        errors = []
        
        max_nodes = constraints.get('Max_Safety_Nodes', float('inf'))
        max_modules = constraints.get('Max_FIO_Modules', float('inf'))
        max_dual_red = constraints.get('Max_Dual_Red_Modules', float('inf'))
        
        if num_nodes > max_nodes:
            errors.append(f"Exceeded max nodes: {num_nodes} > {max_nodes}")
        if num_fio_modules > max_modules:
            errors.append(f"Exceeded max FIO modules: {num_fio_modules} > {max_modules}")
        if num_dual_red_modules > max_dual_red:
            errors.append(f"Exceeded max dual redundant modules: {num_dual_red_modules} > {max_dual_red}")
        
        is_valid = len(errors) == 0
        error_msg = "; ".join(errors) if errors else ""
        
        return is_valid, error_msg
    
    def assign_nodes_and_controllers(self):
        """
        Assign Node, Slot and Controller based on FIO configuration.
        For redundant modules: allocate 2 consecutive slots (odd slot gets signal, even slot reserved for redundancy)
        For non-redundant modules: allocate 1 slot
        """
        print("[DEBUG] Assigning nodes, slots and controllers...")
        
        if self.df_assigned is None or self.df_fio is None:
            print("[ERROR] Required data not loaded")
            return False
        
        # Create node configuration from FIO sheet
        node_config = {}
        for _, row in self.df_fio.iterrows():
            node_num = int(row.get('Node', 0)) if pd.notna(row.get('Node')) else 0
            max_modules = int(row.get('No of Module', 6)) if pd.notna(row.get('No of Module')) else 6
            if node_num > 0:
                node_config[node_num] = {'max_modules': max_modules}
        
        print(f"[DEBUG] Created node config: {node_config}")
        
        # Collect all module instances with their redundancy flags
        assigned_modules = self.df_assigned[self.df_assigned['Module_Instance'] != ""].copy()
        
        # Group by Module_Instance to check if it has redundant signals
        module_redundancy = {}
        for module_instance in assigned_modules['Module_Instance'].unique():
            instance_data = assigned_modules[assigned_modules['Module_Instance'] == module_instance]
            # Check if any signal in this module is marked as redundant
            has_redundant = instance_data['Redundancy_Flag'].eq('Yes').any()
            module_redundancy[module_instance] = has_redundant
        
        # Get already-assigned instances (Node != 0 and != '')
        already_assigned = assigned_modules[(assigned_modules['Node'] != 0) & (assigned_modules['Node'] != '')]
        already_assigned_instances = set(already_assigned['Module_Instance'].unique())
        
        # Get new-to-assign instances
        to_assign = assigned_modules[(assigned_modules['Node'] == 0) | (assigned_modules['Node'] == '')]
        to_assign_instances = sorted(set(to_assign['Module_Instance'].unique()))
        
        print(f"[DEBUG] Module redundancy flags: {module_redundancy}")
        print(f"[DEBUG] To assign instances: {to_assign_instances}")
        
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
                pass
        
        # Find the last assigned position
        current_controller = "SCS0101"
        current_node = 1
        current_slot = 1
        
        if module_assignments:
            last_node = max([assignment[1] for assignment in module_assignments.values()])
            nodes_at_last = [assignment for assignment in module_assignments.values() if assignment[1] == last_node]
            last_slot = max([assignment[2] for assignment in nodes_at_last])
            current_node = last_node
            current_slot = last_slot + 1
        
        print(f"[DEBUG] Starting new assignments from {current_controller}_N{current_node}S{current_slot}")
        
        # Assign new module instances with redundancy handling
        for module_instance in to_assign_instances:
            is_redundant = module_redundancy.get(module_instance, False)
            slots_needed = 2 if is_redundant else 1
            
            print(f"[DEBUG] Processing {module_instance}: redundant={is_redundant}, slots_needed={slots_needed}")
            
            # Ensure we have a valid current_node
            if current_node not in node_config:
                current_node = 1
                controller_num = int(current_controller[3:]) + 1
                current_controller = f"SCS{controller_num:04d}"
                current_slot = 1
            
            max_slots = node_config[current_node]['max_modules']
            
            # Check if we can fit the module in current slot(s)
            if is_redundant:
                # For redundant modules, need 2 consecutive slots
                # If current_slot is even, increment to next odd slot
                if current_slot % 2 == 0:
                    current_slot += 1
                
                if current_slot + 1 <= max_slots:
                    # Assign to odd slot (signal) and even slot (redundancy reserved)
                    module_assignments[module_instance] = (current_controller, current_node, current_slot)
                    print(f"[DEBUG] Assigned {module_instance} (redundant) to {current_controller}_N{current_node}S{current_slot},S{current_slot+1}")
                    current_slot += 2  # Skip to next odd slot
                else:
                    # Current node doesn't have 2 consecutive slots, move to next node
                    current_node += 1
                    current_slot = 1
                    
                    if current_node > max(node_config.keys()):
                        # Need new controller
                        controller_num = int(current_controller[3:]) + 1
                        current_controller = f"SCS{controller_num:04d}"
                        current_node = 1
                        current_slot = 1
                    
                    max_slots = node_config[current_node]['max_modules']
                    module_assignments[module_instance] = (current_controller, current_node, current_slot)
                    print(f"[DEBUG] Assigned {module_instance} (redundant) to {current_controller}_N{current_node}S{current_slot},S{current_slot+1}")
                    current_slot += 2
            else:
                # Non-redundant: single slot
                if current_slot <= max_slots:
                    module_assignments[module_instance] = (current_controller, current_node, current_slot)
                    print(f"[DEBUG] Assigned {module_instance} (non-redundant) to {current_controller}_N{current_node}S{current_slot}")
                    current_slot += 1
                else:
                    # Current node is full, move to next node
                    current_node += 1
                    current_slot = 1
                    
                    if current_node > max(node_config.keys()):
                        # Need new controller
                        controller_num = int(current_controller[3:]) + 1
                        current_controller = f"SCS{controller_num:04d}"
                        current_node = 1
                        current_slot = 1
                    
                    module_assignments[module_instance] = (current_controller, current_node, current_slot)
                    print(f"[DEBUG] Assigned {module_instance} (non-redundant) to {current_controller}_N{current_node}S{current_slot}")
                    current_slot += 1
        
        # Update df_assigned with assignments
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
        
        print(f"[DEBUG] Assigned {assigned_count} instruments to nodes and controllers")
        return True
    
    def identify_unassigned(self):
        """Identify instruments that could not be assigned and sort by Slot then Node"""
        print("[DEBUG] Identifying unassigned instruments...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data")
            return False
        
        self.df_unassigned = self.df_assigned[self.df_assigned['Module_Name'].isna() | (self.df_assigned['Module_Name'] == '')].copy()
        
        # Set Redundancy_Flag for unassigned signals based on IO_REDUNDANCY
        if not self.df_unassigned.empty:
            for idx, row in self.df_unassigned.iterrows():
                io_redundancy = str(row.get('IO_REDUNDANCY', '')).strip()
                if io_redundancy in ['R', 'r', 'Y', 'y', 'Yes', 'YES', 'yes']:
                    self.df_unassigned.at[idx, 'Redundancy_Flag'] = 'Yes'
                else:
                    self.df_unassigned.at[idx, 'Redundancy_Flag'] = 'No'
        
        # Sort by Slot first, then Node
        # Convert Slot and Node to numeric for proper sorting
        if not self.df_unassigned.empty:
            self.df_unassigned['Slot_Sort'] = pd.to_numeric(self.df_unassigned['Slot'], errors='coerce')
            self.df_unassigned['Node_Sort'] = pd.to_numeric(self.df_unassigned['Node'], errors='coerce')
            self.df_unassigned = self.df_unassigned.sort_values(by=['Slot_Sort', 'Node_Sort']).drop(columns=['Slot_Sort', 'Node_Sort'])
        
        print(f"[DEBUG] Found {len(self.df_unassigned)} unassigned instruments")
        if not self.df_unassigned.empty:
            print(f"[DEBUG] Unassigned by IO type: {self.df_unassigned['IO_type'].value_counts().to_dict()}")
        return True
    
    def generate_io_card_summary(self):
        """Generate IO Card Summary with total count of each module type per controller"""
        print("[DEBUG] Generating IO Card Summary...")
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data to summarize")
            return pd.DataFrame()
        
        # Get assigned instruments only
        assigned_df = self.df_assigned[self.df_assigned['Module_Name'] != ""].copy()
        
        if assigned_df.empty:
            print("[ERROR] No assigned instruments to summarize")
            return pd.DataFrame()
        
        # Group by Module_Instance and Controller_No to get unique instances per controller
        module_instance_df = assigned_df[['Module_Instance', 'Module_Name', 'Controller_No']].drop_duplicates()
        
        # Extract module name without instance number (e.g., SAI143-S_1 → SAI143-S)
        module_instance_df['Base_Module'] = module_instance_df['Module_Name']
        
        # Count unique instances per module per controller
        summary_data = []
        for (base_module, controller), group in module_instance_df.groupby(['Base_Module', 'Controller_No']):
            instance_count = len(group)
            summary_data.append({
                'Module_Name': base_module,
                'Controller_No': controller,
                'Qty': instance_count
            })
        
        if not summary_data:
            print("[WARNING] No summary data generated")
            return pd.DataFrame()
        
        # Create pivot table: Module_Name as rows, Controller_No as columns
        summary_df = pd.DataFrame(summary_data)
        card_summary_df = summary_df.pivot_table(index='Module_Name', columns='Controller_No', values='Qty', fill_value=0)
        card_summary_df = card_summary_df.astype(int)
        
        # Add Total column
        card_summary_df['Total'] = card_summary_df.sum(axis=1)
        
        # Reset index to make Module_Name a column
        card_summary_df = card_summary_df.reset_index()
        
        # Rename columns to match expected format
        card_summary_df.columns.name = None
        
        print(f"[DEBUG] Generated IO Card Summary with {len(card_summary_df)} module types")
        print(f"[DEBUG] Modules: {card_summary_df['Module_Name'].tolist()}")
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
            
            # Sort by Slot first (ascending), then by Node (ascending)
            if 'Slot' in assigned_df.columns and 'Node' in assigned_df.columns:
                assigned_df['Slot_Sort'] = pd.to_numeric(assigned_df['Slot'], errors='coerce')
                assigned_df['Node_Sort'] = pd.to_numeric(assigned_df['Node'], errors='coerce')
                assigned_df = assigned_df.sort_values(by=['Slot_Sort', 'Node_Sort']).drop(columns=['Slot_Sort', 'Node_Sort'])
                print("[DEBUG] Sorted assigned sheet by Slot, then Node")
            
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
            
            # Sort assigned data by Node, then Slot, then Channel (as user requested)
            if 'Node' in assigned_df.columns and 'Slot' in assigned_df.columns and 'Channel' in assigned_df.columns:
                assigned_df['Node_Sort'] = pd.to_numeric(assigned_df['Node'], errors='coerce')
                assigned_df['Slot_Sort'] = pd.to_numeric(assigned_df['Slot'], errors='coerce')
                assigned_df['Channel_Sort'] = pd.to_numeric(assigned_df['Channel'], errors='coerce')
                assigned_df = assigned_df.sort_values(by=['Node_Sort', 'Slot_Sort', 'Channel_Sort']).drop(columns=['Node_Sort', 'Slot_Sort', 'Channel_Sort'])
                print("[DEBUG] Sorted assigned sheet by Node (ascending), then Slot (ascending), then Channel (ascending)")
            
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
            
            # Now add Excel formatting and Summary sheet using openpyxl
            from openpyxl import load_workbook
            from openpyxl.utils import get_column_letter
            from openpyxl.worksheet.table import Table, TableStyleInfo
            
            print(f"[DEBUG] Adding Excel formatting and Summary sheet...")
            wb = load_workbook(output_file)
            
            # Format Assigned sheet: auto-fit columns and freeze first row
            if 'Assigned' in wb.sheetnames:
                ws_assigned = wb['Assigned']
                # Freeze first row
                ws_assigned.freeze_panes = 'A2'
                # Auto-fit column widths
                for column in ws_assigned.columns:
                    max_length = 0
                    column_letter = get_column_letter(column[0].column)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50
                    ws_assigned.column_dimensions[column_letter].width = adjusted_width
                print(f"[DEBUG] Formatted Assigned sheet: froze row 1, auto-fitted columns")
            
            # Format Unassigned sheet: auto-fit columns and freeze first row
            if 'Unassigned' in wb.sheetnames:
                ws_unassigned = wb['Unassigned']
                # Freeze first row
                ws_unassigned.freeze_panes = 'A2'
                # Auto-fit column widths
                for column in ws_unassigned.columns:
                    max_length = 0
                    column_letter = get_column_letter(column[0].column)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50
                    ws_unassigned.column_dimensions[column_letter].width = adjusted_width
                print(f"[DEBUG] Formatted Unassigned sheet: froze row 1, auto-fitted columns")
            
            # Create Summary sheet
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
            
            # Format Summary sheet: auto-fit columns
            for column in ws_summary.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50
                ws_summary.column_dimensions[column_letter].width = adjusted_width
            print(f"[DEBUG] Formatted Summary sheet: auto-fitted columns")
            
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
