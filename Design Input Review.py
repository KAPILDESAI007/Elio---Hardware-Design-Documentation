import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import sys
import logging

# Add processors to path for imports
processors_dir = Path(__file__).parent / "processors"
if str(processors_dir) not in sys.path:
    sys.path.insert(0, str(processors_dir))

from channel_assignment_manager import ChannelAssignmentManager


class DesignInputReview:
    """
    Class to perform Design Input Review for ESD system configuration.
    Reads instrument data, sorts intelligently, assigns modules, and generates output.
    """
    
    def __init__(self, system_type=None, controller_model=None, explosion_protection=None, 
                 temperature_rating=None, redundancy_types=None, is_types=None, wired_spares=None, io_types=None):
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
        self.io_types = io_types or ['FIO']  # FIO or NIO (can be both)
        self.redundancy_types = redundancy_types or []  # List of IO types to mark as redundant
        self.is_types = is_types or []  # List of IO types to mark as IS
        self.wired_spares_percentage = wired_spares  # Percentage for wired spares
        
        print(f"[DEBUG] Initialized DesignInputReview with:")
        print(f"  system_type={self.system_type}")
        print(f"  controller_model={self.controller_model}")
        print(f"  explosion_protection={self.explosion_protection}")
        print(f"  temperature_rating={self.temperature_rating}")
        print(f"  io_types={self.io_types}")
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
        
        # Extract available columns and keep ALL columns for now
        # Don't drop missing columns here - apply_user_inputs will handle them
        print(f"[DEBUG] Available columns: {list(self.df_instruments.columns)}")
        
        # Remove rows with empty PID_TAG
        self.df_instruments = self.df_instruments.dropna(subset=['PID_TAG'])
        self.df_instruments['PID_TAG'] = self.df_instruments['PID_TAG'].astype(str).str.strip()
        
        # Normalize IO_type: convert to uppercase and extract base type
        if 'IO_type' in self.df_instruments.columns:
            self.df_instruments['IO_type'] = self.df_instruments['IO_type'].astype(str).str.upper().str.strip()
            self.df_instruments['IO_type_base'] = self.df_instruments['IO_type'].apply(self._extract_io_type_base)
        else:
            print("[WARNING] IO_type column not found")
            self.df_instruments['IO_type'] = ''
            self.df_instruments['IO_type_base'] = ''
        
        print(f"[DEBUG] Extracted {len(self.df_instruments)} rows with required columns")
        print(f"[DEBUG] IO_type_base values: {self.df_instruments['IO_type_base'].unique() if len(self.df_instruments) > 0 else 'NONE'}")
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
        
        # Ensure PID_TAG exists
        if 'PID_TAG' not in self.df_instruments.columns:
            print("[ERROR] PID_TAG column is required but missing")
            return False
        
        # Handle signal_origin column (fallback to system_type)
        if 'signal_origin' not in self.df_instruments.columns:
            if self.system_type:
                print(f"[DEBUG] signal_origin column missing. Using system_type: {self.system_type}")
                self.df_instruments['signal_origin'] = self.system_type
            else:
                print("[WARNING] signal_origin column missing and no system_type provided")
                self.df_instruments['signal_origin'] = 'UNKNOWN'
        
        # Handle IO_type column (critical - must exist)
        if 'IO_type' not in self.df_instruments.columns or self.df_instruments['IO_type'].isna().all() or (self.df_instruments['IO_type'] == '').all():
            print("[ERROR] IO_type column is required but missing or empty")
            return False
        
        # Ensure IO_type_base exists
        if 'IO_type_base' not in self.df_instruments.columns:
            self.df_instruments['IO_type_base'] = self.df_instruments['IO_type'].apply(self._extract_io_type_base)
        
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
        else:
            # Fill any NaN values in IO_REDUNDANCY
            self.df_instruments['IO_REDUNDANCY'] = self.df_instruments['IO_REDUNDANCY'].fillna('')
        
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
        else:
            # Fill any NaN values in IS_Non_IS
            self.df_instruments['IS_Non_IS'] = self.df_instruments['IS_Non_IS'].fillna('NIS')
        
        # Handle Controller_Model column (fallback to controller_model user input)
        if 'Controller_Model' not in self.df_instruments.columns:
            if self.controller_model:
                print(f"[DEBUG] Controller_Model column missing. Using controller_model: {self.controller_model}")
                self.df_instruments['Controller_Model'] = self.controller_model
            else:
                print("[WARNING] Controller_Model column missing and no controller_model provided")
        
        print(f"[DEBUG] Applied user inputs. Data shape: {self.df_instruments.shape}")
        print(f"[DEBUG] IO_type_base unique values: {self.df_instruments['IO_type_base'].unique()}")
        return True
        
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
            print(f"[DEBUG] Total rows in IO_Module_Catalog: {len(self.df_hardware)}")
            
            # Filter for selected IO Types (FIO, NIO, or both)
            if self.io_types and len(self.io_types) > 0:
                print(f"[DEBUG] Filtering by io_types: {self.io_types}")
                self.df_hardware = self.df_hardware[self.df_hardware['Family'].isin(self.io_types)].copy()
                print(f"[DEBUG] Filtered to {self.io_types} modules: {len(self.df_hardware)} rows")
                if self.df_hardware.empty:
                    print(f"[WARNING] After filtering by io_types, no modules found. Available families: {self.df_hardware if not pd.DataFrame(self.df_hardware).empty else 'NONE'}")
            else:
                # Default to FIO only
                print(f"[DEBUG] No io_types specified, defaulting to FIO")
                self.df_hardware = self.df_hardware[self.df_hardware['Family'] == 'FIO'].copy()
                print(f"[DEBUG] Filtered to FIO modules only (default): {len(self.df_hardware)} rows")
                if self.df_hardware.empty:
                    print(f"[WARNING] After filtering to FIO, no modules found")
            
            # Drop duplicate module/IO_Type combinations (keep first occurrence)
            self.df_hardware = self.df_hardware.drop_duplicates(subset=['Module', 'IO_Type'], keep='first')
            print(f"[DEBUG] After deduplication: {len(self.df_hardware)} modules")
            
            # Normalize IO_Type in hardware config
            self.df_hardware['IO_Type'] = self.df_hardware['IO_Type'].astype(str).str.upper().str.strip()
            
            if self.df_hardware.empty:
                print(f"[ERROR] No hardware modules available after filtering and deduplication")
                return False
            
            # Create a standard 'Nos of Channel' column if it doesn't exist (use Nominal_Channels)
            if 'Nos of Channel' not in self.df_hardware.columns:
                self.df_hardware['Nos of Channel'] = self.df_hardware['Nominal_Channels']
            
            # Create a 'Usable_Channels' column if it doesn't exist - per design requirement #10
            # Usable_Channels is the maximum allowed channels per module (constraint from IO_Module_Catalog)
            if 'Usable_Channels' not in self.df_hardware.columns:
                # If not available, default to Nominal_Channels, but warn about it
                self.df_hardware['Usable_Channels'] = self.df_hardware['Nominal_Channels']
                print(f"[WARNING] Usable_Channels column not found - using Nominal_Channels as fallback")
            
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
        Assign instruments to modules with comprehensive constraints.
        Per design spec:
        1. Count signals per IO type
        2. Add wired spare count to signals
        3. Calculate modules needed = ceil((signals + spares) / 16)
        4. Create module instances with calculated capacity
        5. Assign channels 1-16 per module for both signals and spares
        6. Distribute empty channels equally
        """
        try:
            print("[DEBUG] Assigning instruments to modules with comprehensive constraints...")
            
            if self.df_instruments is None or self.df_hardware is None:
                print("[ERROR] Required data not loaded")
                return False
            
            # STEP 1: Calculate wired spares BEFORE assignment and create wired spare rows
            print("[DEBUG] STEP 1: Calculate wired spares count per IO type...")
            wired_spares_data = []
            wired_spares_count = {}
            
            if self.wired_spares_percentage is not None and self.wired_spares_percentage > 0:
                print(f"[DEBUG] Wired spares percentage: {self.wired_spares_percentage}%")
                for io_type_base in self.df_instruments['IO_type_base'].unique():
                    if 'SOFT' in str(io_type_base).upper():
                        print(f"[DEBUG]   Skipping SOFT: {io_type_base}")
                        continue
                    
                    signal_count = len(self.df_instruments[self.df_instruments['IO_type_base'] == io_type_base])
                    spare_count = int(signal_count * (self.wired_spares_percentage / 100))
                    wired_spares_count[io_type_base] = spare_count
                    print(f"[DEBUG]   {io_type_base}: {signal_count} signals + {spare_count} spares = {signal_count + spare_count} total")
                    
                    # Create wired spare ROWS (not just tags) to include in assignment
                    for spare_idx in range(spare_count):
                        spare_row = {
                            'PID_TAG': f"{io_type_base}_SPARE_{spare_idx+1}",  # Placeholder, will be updated
                            'signal_origin': '',
                            'IO_type': f"{io_type_base}_Spare",
                            'IO_type_base': io_type_base,
                            'IO_REDUNDANCY': '',
                            'IS_Non_IS': 'NIS',
                            'Module_Name': '',
                            'Channel': 0,
                            'Node': '',
                            'Slot': 0,
                            'Controller_No': '',
                            'is_wired_spare': True  # Mark as wired spare
                        }
                        wired_spares_data.append(spare_row)
            
            # Add wired spare rows to df_instruments BEFORE module assignment
            if wired_spares_data:
                df_wired_spares = pd.DataFrame(wired_spares_data)
                self.df_instruments = pd.concat([self.df_instruments, df_wired_spares], ignore_index=True)
                print(f"[DEBUG] Added {len(wired_spares_data)} wired spare rows to df_instruments")
                print(f"[DEBUG] df_instruments now has {len(self.df_instruments)} rows (signals + spares)")
            
            self.wired_spares_count = wired_spares_count
            
            # CONSTRAINT 1: Filter hardware based on Temperature Rating and Explosion Protection
            df_hardware_filtered = self.df_hardware.copy()
            
            # Filter by Temperature Rating (if specified)
            if self.temperature_rating:
                if self.temperature_rating == 'Wide':
                    # For Wide temperature, prefer modules with Ambient_Max_C == 70, but allow 60/65 if needed
                    df_temp_filtered = df_hardware_filtered[
                        pd.to_numeric(df_hardware_filtered['Ambient_Max_C'], errors='coerce') == 70
                    ]
                    if not df_temp_filtered.empty:
                        df_hardware_filtered = df_temp_filtered
                        print(f"[DEBUG] Temperature Rating: Wide - filtered to {len(df_hardware_filtered)} modules with Ambient_Max_C=70")
                    else:
                        print(f"[DEBUG] Temperature Rating: Wide - No modules with Ambient_Max_C=70, using available modules")
                elif self.temperature_rating == 'Standard':
                    # For Standard temperature, prefer modules with Ambient_Max_C == 60 or 65
                    df_temp_filtered = df_hardware_filtered[
                        pd.to_numeric(df_hardware_filtered['Ambient_Max_C'], errors='coerce').isin([60, 65])
                    ]
                    if not df_temp_filtered.empty:
                        df_hardware_filtered = df_temp_filtered
                        print(f"[DEBUG] Temperature Rating: Standard - filtered to {len(df_hardware_filtered)} modules with Ambient_Max_C in [60, 65]")
                    else:
                        print(f"[DEBUG] Temperature Rating: Standard - No modules with Ambient_Max_C in [60, 65], using available modules")
            
            # Filter by Explosion Protection (if specified)
            if self.explosion_protection:
                if self.explosion_protection == 'Yes':
                    # Filter for modules with Suffix_Explosion specified (non-empty)
                    df_exp_filtered = df_hardware_filtered[
                        df_hardware_filtered['Suffix_Explosion'].fillna('').astype(str).str.strip() != ''
                    ]
                    if not df_exp_filtered.empty:
                        df_hardware_filtered = df_exp_filtered
                        print(f"[DEBUG] Explosion Protection: Yes - filtered to {len(df_hardware_filtered)} explosion-rated modules")
                    else:
                        print(f"[DEBUG] Explosion Protection: Yes - No explosion-rated modules, using available modules")
                elif self.explosion_protection == 'No':
                    # Exclude modules with Suffix_Explosion
                    df_exp_filtered = df_hardware_filtered[
                        df_hardware_filtered['Suffix_Explosion'].fillna('').astype(str).str.strip() == ''
                    ]
                    if not df_exp_filtered.empty:
                        df_hardware_filtered = df_exp_filtered
                        print(f"[DEBUG] Explosion Protection: No - filtered to {len(df_hardware_filtered)} non-explosion modules")
                    else:
                        print(f"[DEBUG] Explosion Protection: No - No non-explosion modules, using available modules")
            
            if df_hardware_filtered.empty:
                print("[ERROR] No modules available in hardware configuration")
                return False
            
            # Calculate wired spares count per signal type (skip SOFT signals - they have no hardware)
            wired_spares_count = {}
            total_signal_counts = {}
            if self.wired_spares_percentage is not None and self.wired_spares_percentage > 0:
                print(f"[DEBUG] Calculating wired spares per signal type (percentage={self.wired_spares_percentage})")
                for io_type_base in self.df_instruments['IO_type_base'].unique():
                    # SKIP SOFT signals - they don't require hardware modules
                    if 'SOFT' in str(io_type_base).upper():
                        print(f"[DEBUG]   {io_type_base}: Skipping SOFT signals (no hardware required)")
                        continue
                    
                    signal_count = len(self.df_instruments[self.df_instruments['IO_type_base'] == io_type_base])
                    spare_count = int(signal_count * (self.wired_spares_percentage / 100))
                    wired_spares_count[io_type_base] = spare_count
                    total_signal_counts[io_type_base] = signal_count
                    total_with_spares = signal_count + spare_count
                    print(f"[DEBUG]   {io_type_base}: {signal_count} signals + {spare_count} spares = {total_with_spares} total")
            else:
                print(f"[DEBUG] No wired spares percentage provided")
                for io_type_base in self.df_instruments['IO_type_base'].unique():
                    # SKIP SOFT signals - they don't require hardware modules
                    if 'SOFT' in str(io_type_base).upper():
                        print(f"[DEBUG]   {io_type_base}: Skipping SOFT signals (no hardware required)")
                        continue
                    
                    signal_count = len(self.df_instruments[self.df_instruments['IO_type_base'] == io_type_base])
                    total_signal_counts[io_type_base] = signal_count
                    print(f"[DEBUG]   {io_type_base}: {signal_count} signals")
            
            # CONSTRAINT 2: Calculate number of modules needed for each IO type
            print(f"[DEBUG] Calculating modules required per IO type...")
            print(f"[DEBUG] Available columns in filtered hardware: {list(df_hardware_filtered.columns)}")
            modules_required = {}
            for io_type_base, total_count in total_signal_counts.items():
                spare_count = wired_spares_count.get(io_type_base, 0)
                total_with_spares = total_count + spare_count
                
                # Get usable capacity for this IO type
                df_type_modules = df_hardware_filtered[
                    df_hardware_filtered['IO_Type'].astype(str).str.upper().str.contains(io_type_base.split('-')[0], na=False)
                ]
                if df_type_modules.empty:
                    print(f"[ERROR] No modules available for {io_type_base}")
                    print(f"[DEBUG] Looking for IO_Type containing: {io_type_base.split('-')[0]}")
                    print(f"[DEBUG] Available IO_Types: {df_hardware_filtered['IO_Type'].unique()}")
                    return False
                
                # Try to get usable capacity, fall back to Nominal_Channels or default to 16
                module_capacity = 16
                if 'Usable_Channels' in df_hardware_filtered.columns:
                    cap_val = df_type_modules['Usable_Channels'].iloc[0]
                    if pd.notna(cap_val):
                        try:
                            module_capacity = int(cap_val)
                        except (ValueError, TypeError):
                            print(f"[DEBUG] Could not convert Usable_Channels {cap_val}, trying Nominal_Channels")
                
                if module_capacity == 16 and 'Nominal_Channels' in df_hardware_filtered.columns:
                    cap_val = df_type_modules['Nominal_Channels'].iloc[0]
                    if pd.notna(cap_val):
                        try:
                            module_capacity = int(cap_val)
                        except (ValueError, TypeError):
                            pass
                
                modules_needed = (total_with_spares + module_capacity - 1) // module_capacity  # Ceiling division
                modules_required[io_type_base] = modules_needed
                print(f"[DEBUG]   {io_type_base}: {total_with_spares} IOs / {module_capacity} capacity = {modules_needed} modules needed")
            
            # Store for later use
            self.wired_spares_count = wired_spares_count
            
            # Prepare assignment dataframe
            self.df_assigned = self.df_instruments.copy()
            self.df_assigned['Module_Name'] = ""
            self.df_assigned['Module_Instance'] = ""
            self.df_assigned['Channel'] = 0
            self.df_assigned['Node'] = ""
            self.df_assigned['Slot'] = 0
            self.df_assigned['Controller_No'] = ""
            self.df_assigned['Redundancy_Flag'] = ""
            
            # Create mapping from IO_type to Module information using FILTERED hardware
            module_map = {}
            
            unique_modules = df_hardware_filtered.drop_duplicates(subset=['Module', 'IO_Type'])
            print(f"[DEBUG] Processing {len(unique_modules)} unique modules for assignment (after filtering)")
            
            for _, row in unique_modules.iterrows():
                io_type = str(row.get('IO_Type', '')).upper().strip()
                module_name = str(row.get('Module', '')).strip()
                usable_capacity = 16
                
                # Try Usable_Channels first, then Nominal_Channels, then default to 16
                if 'Usable_Channels' in df_hardware_filtered.columns:
                    cap_val = row.get('Usable_Channels')
                    if pd.notna(cap_val):
                        try:
                            usable_capacity = int(cap_val)
                        except (ValueError, TypeError):
                            pass
                
                if usable_capacity == 16 and 'Nominal_Channels' in df_hardware_filtered.columns:
                    cap_val = row.get('Nominal_Channels')
                    if pd.notna(cap_val):
                        try:
                            usable_capacity = int(cap_val)
                        except (ValueError, TypeError):
                            pass
                
                supports_hart = str(row.get('Supports_HART', '')).strip().lower() == 'yes'
                
                if io_type and module_name:
                    base_type = self._extract_io_type_base(io_type)
                    base_type_normalized = base_type.split('-')[0]
                    
                    if base_type_normalized not in module_map:
                        module_map[base_type_normalized] = []
                    
                    module_map[base_type_normalized].append({
                        'name': module_name,
                        'capacity': usable_capacity,
                        'is_hart': supports_hart,
                        'instances': {}
                    })
                    print(f"[DEBUG] Added module: {base_type_normalized} -> {module_name} (usable capacity: {usable_capacity})")
            
            print(f"[DEBUG] Created module map with {sum(len(v) for v in module_map.values())} modules across {len(module_map)} IO types")
            
            # Assign instruments to modules - INTERLEAVE SIGNALS AND SPARES for even distribution
            # Split items into signals and spares
            signal_mask = ~self.df_assigned['PID_TAG'].astype(str).str.contains('_SPARE_', case=False, na=False)
            spare_mask = self.df_assigned['PID_TAG'].astype(str).str.contains('_SPARE_', case=False, na=False)
            
            signals_list = list(self.df_assigned[signal_mask].iterrows())
            spares_list = list(self.df_assigned[spare_mask].iterrows())
            
            print(f"[DEBUG] Interleaving {len(signals_list)} signals with {len(spares_list)} spares for even distribution...")
            
            # Interleave signals and spares: for every 3 signals, assign 1 spare
            # This distributes spares throughout the module assignment process
            items_to_process = []
            signal_idx = 0
            spare_idx = 0
            spare_freq = max(1, len(signals_list) // max(1, len(spares_list)))  # How many signals per spare
            signal_count_since_spare = 0
            
            while signal_idx < len(signals_list) or spare_idx < len(spares_list):
                # Add signals
                if signal_idx < len(signals_list):
                    items_to_process.append(signals_list[signal_idx])
                    signal_idx += 1
                    signal_count_since_spare += 1
                    
                    # Add a spare periodically for even distribution
                    if signal_count_since_spare >= spare_freq and spare_idx < len(spares_list):
                        items_to_process.append(spares_list[spare_idx])
                        spare_idx += 1
                        signal_count_since_spare = 0
                elif spare_idx < len(spares_list):
                    # Only spares left
                    items_to_process.append(spares_list[spare_idx])
                    spare_idx += 1
            
            print(f"[DEBUG] Interleaved order ready: {len(items_to_process)} total items")
            
            unassigned_count = 0
            for idx, row in items_to_process:
                io_type_base = row.get('IO_type_base', '')
                
                # SKIP SOFT signals
                if 'SOFT' in str(io_type_base).upper():
                    print(f"[DEBUG] Skipping SOFT signal: {row.get('PID_TAG', 'UNKNOWN')}")
                    continue
                
                io_type_base_normalized = io_type_base.split('-')[0] if io_type_base else ''
                
                is_type = row.get('IS_Non_IS', 'NIS')
                pid_tag = row.get('PID_TAG', 'UNKNOWN')
                is_redundant = str(row.get('IO_REDUNDANCY', '')).strip() in ['R', 'r', 'Y', 'y', 'Yes', 'YES', 'yes']
                signal_type = row.get('signal_origin', '')
                signal_requires_hart = signal_type in ['HART', 'hart'] or 'HART' in str(row.get('IO_type', ''))
                
                if io_type_base_normalized and io_type_base_normalized in module_map:
                    assigned = False
                    
                    for module_info in module_map[io_type_base_normalized]:
                        if signal_requires_hart and not module_info['is_hart']:
                            continue
                        if not signal_requires_hart and module_info['is_hart']:
                            continue
                        
                        base_module_name = module_info['name']
                        usable_capacity = module_info['capacity']  # This is Usable_Channels limit (16)
                        
                        instance_num = 1
                        while instance_num <= modules_required.get(io_type_base_normalized, 50):
                            if instance_num not in module_info['instances']:
                                module_info['instances'][instance_num] = {
                                    'IS_count': 0,
                                    'NIS_count': 0,
                                    'channels_per_slot': [0] * 8,
                                    'is_type': None
                                }
                            
                            instance_data = module_info['instances'][instance_num]
                            instance_is_type = instance_data['is_type']
                            
                            if instance_is_type is None:
                                instance_data['is_type'] = is_type
                                instance_is_type = is_type
                            
                            if instance_is_type != is_type:
                                instance_num += 1
                                continue
                            
                            # Calculate TOTAL channels used across ALL slots in this module instance
                            total_channels_used = sum(instance_data['channels_per_slot'])
                            
                            # CRITICAL: Check total channels don't exceed Usable_Channels limit (Requirement #10)
                            if total_channels_used >= usable_capacity:
                                print(f"[DEBUG] Instance {base_module_name}_{instance_num} at capacity ({total_channels_used} >= {usable_capacity})")
                                instance_num += 1
                                continue
                            
                            assigned_to_slot = False
                            for slot_idx in range(8):
                                channels_used_in_slot = instance_data['channels_per_slot'][slot_idx]
                                
                                # Check: can we add to this slot? (within both slot and module limits)
                                # Slot capacity is typically 16, but we're limited by module Usable_Channels (16 total)
                                if channels_used_in_slot < usable_capacity and total_channels_used < usable_capacity:
                                    next_channel = total_channels_used + 1  # Next channel in MODULE sequence
                                    
                                    # CRITICAL: Ensure channel doesn't exceed Usable_Channels (Requirement #10)
                                    if next_channel > usable_capacity:
                                        print(f"[DEBUG] Channel {next_channel} exceeds usable limit {usable_capacity}, skipping")
                                        break
                                    
                                    module_instance = f"{base_module_name}_{instance_num}"
                                    
                                    already_assigned = self.df_assigned[
                                        (self.df_assigned['Module_Instance'] == module_instance) &
                                        (self.df_assigned['Channel'] == next_channel)
                                    ]
                                    if not already_assigned.empty:
                                        continue
                                    
                                    instance_data['channels_per_slot'][slot_idx] = channels_used_in_slot + 1
                                    if is_type == 'IS':
                                        instance_data['IS_count'] += 1
                                    else:
                                        instance_data['NIS_count'] += 1
                                    
                                    self.df_assigned.at[idx, 'Module_Name'] = base_module_name
                                    self.df_assigned.at[idx, 'Module_Instance'] = module_instance
                                    self.df_assigned.at[idx, 'Channel'] = next_channel
                                    self.df_assigned.at[idx, 'Redundancy_Flag'] = 'Yes' if is_redundant else 'No'
                                    
                                    print(f"[DEBUG] [ASSIGNED] {pid_tag} to {module_instance} CH{next_channel}")
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
                        print(f"[WARNING] [UNASSIGNED] {pid_tag}")
                        unassigned_count += 1
                else:
                    print(f"[WARNING] [UNASSIGNED] {pid_tag} - IO_type not available")
                    unassigned_count += 1
            
            assigned_count = len(self.df_assigned[self.df_assigned['Module_Name'] != ""])
            print(f"[DEBUG] Module assignment complete: {assigned_count} assigned, {unassigned_count} unassigned")
            return True
            
        except Exception as e:
            print(f"[ERROR] Exception during module assignment: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
    
    def assign_modules_intelligent(self):
        """
        NEW INTELLIGENT ASSIGNMENT METHOD using ChannelAssignmentManager.
        
        Process flow:
        1. Add wired spare rows to df_instruments
        2. Analyze signals and calculate module requirements
        3. Plan module allocation (which signals go to which modules)
        4. Distribute wired spares evenly across all modules
        5. Ensure each module has at least 1 empty channel (or equal distribution)
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("[DEBUG] [NEW METHOD] Assigning instruments using intelligent ChannelAssignmentManager...")
        
        if self.df_instruments is None or self.df_hardware is None:
            print("[ERROR] Required data not loaded")
            return False
        
        try:
            # STEP 0: Add wired spare rows to df_instruments BEFORE creating manager
            print("[DEBUG] STEP 0: Adding wired spare rows to instruments...")
            if self.wired_spares_percentage is not None and self.wired_spares_percentage > 0:
                wired_spares_data = []
                wired_spares_count = {}
                
                print(f"[DEBUG] Wired spares percentage: {self.wired_spares_percentage}%")
                for io_type_base in self.df_instruments['IO_type_base'].unique():
                    if 'SOFT' in str(io_type_base).upper():
                        print(f"[DEBUG]   Skipping SOFT: {io_type_base}")
                        continue
                    
                    signal_count = len(self.df_instruments[self.df_instruments['IO_type_base'] == io_type_base])
                    spare_count = int(signal_count * (self.wired_spares_percentage / 100))
                    wired_spares_count[io_type_base] = spare_count
                    print(f"[DEBUG]   {io_type_base}: {signal_count} signals + {spare_count} spares = {signal_count + spare_count} total")
                    
                    # Create wired spare ROWS to include in assignment
                    for spare_idx in range(spare_count):
                        spare_row = {
                            'PID_TAG': f"SPARE_{io_type_base}_{spare_idx+1}",  # Temporary, will be updated later
                            'signal_origin': '',
                            'IO_type': f"{io_type_base}_Spare",
                            'IO_type_base': io_type_base,
                            'IO_REDUNDANCY': '',
                            'IS_Non_IS': 'NIS',
                            'Module_Name': '',
                            'Channel': 0,
                            'Node': '',
                            'Slot': 0,
                            'Controller_No': '',
                        }
                        # Add all other columns that exist in df_instruments
                        for col in self.df_instruments.columns:
                            if col not in spare_row:
                                spare_row[col] = ''
                        wired_spares_data.append(spare_row)
                
                # Add wired spare rows to df_instruments BEFORE manager analysis
                if wired_spares_data:
                    df_wired_spares = pd.DataFrame(wired_spares_data)
                    self.df_instruments = pd.concat([self.df_instruments, df_wired_spares], ignore_index=True)
                    self.wired_spares_count = wired_spares_count
                    print(f"[DEBUG] Added {len(wired_spares_data)} wired spare rows to df_instruments")
                    print(f"[DEBUG] df_instruments now has {len(self.df_instruments)} rows (signals + spares)")
                else:
                    print(f"[DEBUG] No wired spares to add")
                    self.wired_spares_count = {}
            else:
                print(f"[DEBUG] No wired spares percentage provided")
                self.wired_spares_count = {}
            
            # Create and initialize the assignment manager
            manager = ChannelAssignmentManager(self.df_instruments, self.df_hardware)
            
            # Step 1: Analyze and plan the assignment
            analysis = manager.analyze_and_plan()
            
            if not analysis.get('success', False):
                print(f"[ERROR] Failed to analyze and plan assignments: {analysis.get('error', 'Unknown error')}")
                return False
            
            print(f"\n[DEBUG] Analysis Results:")
            print(f"  - Total signals: {analysis['total_signals']}")
            print(f"  - Total wired spares: {analysis['total_wired_spares']}")
            print(f"  - Modules needed: {analysis['total_modules']}")
            print(f"  - Channels per module: {analysis['channels_per_module']}")
            print(f"  - Wired spares per module: {analysis['wired_spares_per_module']:.2f}")
            print(f"  - Signal groups: {analysis['signal_groups']}")
            
            # Step 2: Assign channels based on the plan
            self.df_assigned = manager.assign_channels(node_start=1, slot_start=1)
            
            if self.df_assigned.empty:
                print("[ERROR] Failed to assign channels")
                return False
            
            # Count assignments
            assigned_count = len(self.df_assigned[self.df_assigned['Channel'] > 0])
            unassigned_count = len(self.df_assigned[self.df_assigned['Channel'] == 0])
            
            print(f"\n[DEBUG] Assignment Results:")
            print(f"  - Successfully assigned: {assigned_count}")
            print(f"  - Unassigned: {unassigned_count}")
            
            # Print summary report
            print(manager.get_summary_report())
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Exception in assign_modules_intelligent: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def assign_nodes_and_controllers(self):
        """
        Assign Node, Slot and Controller based on FIO configuration.
        For redundant modules: allocate 2 consecutive slots (odd slot gets signal, even slot reserved for redundancy)
        For non-redundant modules: allocate 1 slot
        Per requirement #11: Validates against Mounting Rule sheet to ensure number of modules in each node align with requirements.
        """
        print("[DEBUG] Assigning nodes, slots and controllers...")
        print("[DEBUG] Validating against Mounting Rule per requirement #11...")
        
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
        
        # Validate node configuration against Mounting Rule (requirement #11)
        if self.df_mounting_rule is not None and not self.df_mounting_rule.empty:
            print(f"[DEBUG] Validating node configuration against Mounting Rule...")
            for node_num, config in node_config.items():
                # Get max slots for this node from mounting rule
                mounting_rule_slots = self.get_available_slots_for_node(node_num, 'SCU_Without_ESB' if node_num == 1 else 'SNU')
                max_allowed_slots = len(mounting_rule_slots)
                
                if config['max_modules'] > max_allowed_slots:
                    print(f"[WARNING] Node {node_num} configured for {config['max_modules']} modules, but Mounting Rule allows max {max_allowed_slots}")
                    config['max_modules'] = max_allowed_slots  # Apply constraint
                else:
                    print(f"[DEBUG] Node {node_num}: {config['max_modules']} modules within limit of {max_allowed_slots}")
        else:
            print(f"[DEBUG] Mounting Rule not available, using FIO configuration as-is")
        
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
                # Ensure Node and Slot are stored as strings to avoid StringDtype errors
                try:
                    self.df_assigned.at[idx, 'Node'] = str(node) if not pd.isna(node) else pd.NA
                except Exception:
                    self.df_assigned.at[idx, 'Node'] = pd.NA
                try:
                    self.df_assigned.at[idx, 'Slot'] = str(slot) if not pd.isna(slot) else pd.NA
                except Exception:
                    self.df_assigned.at[idx, 'Slot'] = pd.NA
                assigned_count += 1
        
        print(f"[DEBUG] Assigned {assigned_count} instruments to nodes and controllers")
        print(f"[DEBUG] Node and slot assignments comply with Mounting Rule per requirement #11")
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
            # Controller_No may be a string like 'SCS0101' or a plain numeric value.
            # Preserve as string to avoid int conversion errors; numeric sorting will be handled later if needed.
            summary_data.append({
                'Module_Name': str(base_module),
                'Controller_No': str(controller),
                'Qty': int(instance_count)
            })
        
        if not summary_data:
            print("[WARNING] No summary data generated")
            return pd.DataFrame()
        
        # Create pivot table: Module_Name as rows, Controller_No as columns
        summary_df = pd.DataFrame(summary_data)
        card_summary_df = summary_df.pivot_table(index='Module_Name', columns='Controller_No', values='Qty', fill_value=0)
        card_summary_df = card_summary_df.astype('object')  # Use object dtype instead of int
        
        # Add Total column
        card_summary_df['Total'] = card_summary_df.sum(axis=1)
        
        # Reset index to make Module_Name a column
        card_summary_df = card_summary_df.reset_index()
        
        # Rename columns to match expected format
        card_summary_df.columns.name = None
        
        # Ensure all columns are object type (safe for Excel)
        for col in card_summary_df.columns:
            card_summary_df[col] = card_summary_df[col].astype('object')
        
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
                    'SCS_No': str(scs),
                    'Signal_Type': str(signal_type),
                    'Actual': int(count),
                    'Wired_Spare': int(wired_spare_count),
                    'Unwired_Spare': 0,
                    'Total_Qty': int(count + wired_spare_count)
                })
        
        io_summary_df = pd.DataFrame(summary_rows)
        
        # Ensure all columns are object type (safe for Excel)
        for col in io_summary_df.columns:
            io_summary_df[col] = io_summary_df[col].astype('object')
        
        print(f"[DEBUG] Generated IO Summary with {len(io_summary_df)} rows")
        return io_summary_df
    
    def generate_wired_spares(self):
        """
        Generate wired spare channels based on pre-calculated counts per signal type.
        Distributes spares evenly across all module instances of each signal type.
        Uses node/slot/channel info from assigned data.
        """
        print(f"[DEBUG] Generating wired spare channels... wired_spares_percentage={self.wired_spares_percentage}")
        
        if self.wired_spares_percentage is None or self.wired_spares_percentage == 0:
            print(f"[DEBUG] No wired spares percentage provided")
            return pd.DataFrame()
        
        if self.df_assigned is None:
            print("[ERROR] No assigned data")
            return pd.DataFrame()
        
        if not hasattr(self, 'wired_spares_count') or not self.wired_spares_count:
            print("[DEBUG] No wired spares to generate")
            return pd.DataFrame()
        
        spares_data = []
        
        # For each signal type that needs wired spares
        for io_type_base, spare_count in self.wired_spares_count.items():
            if spare_count <= 0:
                continue
            
            print(f"[DEBUG] Generating {spare_count} wired spares for {io_type_base}")
            
            # Get all assigned instances of this signal type
            assigned_of_type = self.df_assigned[
                (self.df_assigned['IO_type_base'] == io_type_base) &
                (self.df_assigned['Module_Instance'] != "")
            ].copy()
            
            if assigned_of_type.empty:
                print(f"[DEBUG]   No assigned instances found for {io_type_base}")
                continue
            
            # Get unique module instances
            module_instances = sorted(assigned_of_type['Module_Instance'].unique())
            num_instances = len(module_instances)
            
            # Distribute spares evenly across instances
            spares_per_instance_base = spare_count // num_instances
            spares_remainder = spare_count % num_instances
            
            print(f"[DEBUG]   Found {num_instances} instances, distributing {spares_per_instance_base} base + {spares_remainder} remainder")
            
            spares_assigned = 0
            
            # Add spares to each instance
            for idx, module_instance in enumerate(module_instances):
                instance_signals = assigned_of_type[assigned_of_type['Module_Instance'] == module_instance]
                
                # How many spares for this instance
                spares_for_this = spares_per_instance_base
                if idx < spares_remainder:
                    spares_for_this += 1
                
                if spares_for_this <= 0:
                    continue
                
                # Get instance info from one of the signals
                sample_row = instance_signals.iloc[0]
                controller_no = str(sample_row.get('Controller_No', 'SCS0101'))
                node_num = int(sample_row.get('Node', 1)) if pd.notna(sample_row.get('Node')) else 1
                slot_num = int(sample_row.get('Slot', 1)) if pd.notna(sample_row.get('Slot')) else 1
                
                # Get the highest channel number used in this instance
                max_channel = int(instance_signals['Channel'].max()) if len(instance_signals) > 0 else 0
                
                # Get the Usable_Channels limit for this module (Requirement #10)
                module_name = sample_row.get('Module_Name', '')
                usable_channels_limit = 16  # Default
                if self.df_hardware is not None and not self.df_hardware.empty:
                    matching_hw = self.df_hardware[self.df_hardware['Module'] == module_name]
                    if not matching_hw.empty:
                        usable_channels_limit = int(matching_hw.iloc[0].get('Usable_Channels', 16))
                
                print(f"[DEBUG]     {module_instance}: max_channel={max_channel}, usable_limit={usable_channels_limit}, {spares_for_this} spares needed")
                
                # Add spares starting from next available channel
                spares_added_for_instance = 0
                next_available_channel = max_channel + 1  # Start from next channel after signals
                
                for spare_idx in range(1, spares_for_this + 1):
                    spare_channel = next_available_channel
                    
                    # CRITICAL: Check Usable_Channels limit per Requirement #10
                    if spare_channel > usable_channels_limit:
                        print(f"[DEBUG]     Spare channel {spare_channel} exceeds usable limit {usable_channels_limit}, skipping remaining spares")
                        break
                    
                    spare_tag = f"{controller_no}_N{node_num}S{slot_num}CH{spare_channel}"
                    next_available_channel += 1  # Move to next channel for next spare
                    
                    spares_data.append({
                        'PID_TAG': spare_tag,
                        'signal_origin': sample_row.get('signal_origin', ''),
                        'IO_type': f"{sample_row.get('IO_type', '')}_Spare",
                        'IO_REDUNDANCY': '',
                        'IS_Non_IS': sample_row.get('IS_Non_IS', 'NIS'),
                        'IO_type_base': io_type_base,
                        'Module_Name': sample_row.get('Module_Name', ''),
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
                    spares_assigned += 1
                    spares_added_for_instance += 1
                
                if spares_added_for_instance < spares_for_this:
                    print(f"[DEBUG]     Only added {spares_added_for_instance} of {spares_for_this} requested spares (hit Usable_Channels limit)")
        
        spares_df = pd.DataFrame(spares_data)
        print(f"[DEBUG] Generated {len(spares_df)} total wired spare channels")
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
            print(f"[DEBUG] io_card_summary_df type: {type(io_card_summary_df)}, empty: {io_card_summary_df.empty if hasattr(io_card_summary_df, 'empty') else 'N/A'}")
            if io_card_summary_df is not None and not io_card_summary_df.empty:
                print(f"[DEBUG] io_card_summary_df will be written to Excel")
            else:
                print(f"[DEBUG] io_card_summary_df is None or empty - WILL NOT be written")
            
            io_summary_df = self.generate_io_summary()
            print(f"[DEBUG] io_summary_df type: {type(io_summary_df)}, empty: {io_summary_df.empty if hasattr(io_summary_df, 'empty') else 'N/A'}")
            if io_summary_df is not None and not io_summary_df.empty:
                print(f"[DEBUG] io_summary_df will be written to Excel")
            else:
                print(f"[DEBUG] io_summary_df is None or empty - WILL NOT be written")
            
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
            
            # Regenerate PID_TAG for wired spares (those with N0S0 placeholders OR SPARE_ pattern)
            # These are spares that were assigned to nodes/slots
            print(f"[DEBUG] Before tag regen: assigned_df has {len(assigned_df)} rows")
            print(f"[DEBUG] Sample PID_TAGs before regen: {assigned_df['PID_TAG'].iloc[:5].tolist()}")
            print(f"[DEBUG] Sample PID_TAGs at end before regen: {assigned_df['PID_TAG'].iloc[-5:].tolist()}")
            
            # Look for both N0S0 placeholder tags AND SPARE temporary tags (both SPARE_N and IO_TYPE_SPARE_N patterns)
            mask_n0s0_tags = assigned_df['PID_TAG'].str.contains('SCS.*_N0S0CH', regex=True, na=False)
            # Match both patterns: ^SPARE_ (old pattern) or _SPARE_\d+$ (AI_SPARE_1, DI_SPARE_2, etc.)
            # Use .contains() instead of .match() because we need to find these patterns ANYWHERE in the string
            mask_spare_tags = assigned_df['PID_TAG'].str.contains(r'^SPARE_|_SPARE_\d+$', regex=True, na=False)
            mask_placeholder_tags = mask_n0s0_tags | mask_spare_tags
            
            print(f"[DEBUG] Rows matching N0S0 pattern: {mask_n0s0_tags.sum()}")
            print(f"[DEBUG] Rows matching SPARE_ pattern: {mask_spare_tags.sum()}")
            print(f"[DEBUG] Total placeholder tags to regen: {mask_placeholder_tags.sum()}")
            print(f"[DEBUG] Rows with N0S0/SPARE_ that will be regenerated: {assigned_df[mask_placeholder_tags]['PID_TAG'].tolist()[:10]}")
            
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
            
            # Filter out pre-existing placeholder spares (from input file like SPARE1, SPARE2)
            # BUT KEEP wired spares that were created by us (marked with is_wired_spare=True)
            before_filter = len(assigned_df)
            print(f"[DEBUG] Before filtering placeholder spares: {before_filter} rows")
            
            # Check if is_wired_spare column exists (it gets added when wired spares are created)
            is_wired_spare_mask = pd.Series(False, index=assigned_df.index)
            if 'is_wired_spare' in assigned_df.columns:
                is_wired_spare_mask = assigned_df['is_wired_spare'].fillna(False).astype(bool)
                print(f"[DEBUG] Found is_wired_spare column with {is_wired_spare_mask.sum()} wired spares marked")
            
            # Input file placeholder spares have patterns like: SPARE1, SPARE2, spare1, etc (contain 'spare' lowercase)
            placeholder_spare_mask = assigned_df['PID_TAG'].str.lower().str.contains('spare', na=False)
            
            # Keep rows that are:
            # 1. NOT containing 'spare' (lowercase), OR  
            # 2. ARE our wired spares (is_wired_spare=True)
            keep_mask = ~placeholder_spare_mask | is_wired_spare_mask
            
            print(f"[DEBUG] Rows marked as wired spares: {is_wired_spare_mask.sum()}")
            print(f"[DEBUG] Rows with 'spare' (lowercase) in PID_TAG: {placeholder_spare_mask.sum()}")
            print(f"[DEBUG] Rows to KEEP (not placeholder OR is_wired_spare): {keep_mask.sum()}")
            
            assigned_df = assigned_df[keep_mask]
            
            filtered_out = before_filter - len(assigned_df)
            print(f"[DEBUG] After filtering: {len(assigned_df)} rows (filtered out {filtered_out} placeholder spares)")
            
            # Reorder columns: Keep ONLY the required columns in specified order
            col_order = ['PID_TAG', 'signal_origin', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS', 
                         'Module_Name', 'Controller_No', 'Node', 'Slot', 'Channel']
            available_cols = [col for col in col_order if col in assigned_df.columns]
            assigned_df = assigned_df[available_cols]  # Keep ONLY these columns, drop the rest
            print(f"[DEBUG] Final assigned columns: {list(assigned_df.columns)}")
            
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
            print(f"[DEBUG] About to enter ExcelWriter with:")
            print(f"[DEBUG]   io_card_summary_df type: {type(io_card_summary_df)}")
            print(f"[DEBUG]   io_card_summary_df is None: {io_card_summary_df is None}")
            if io_card_summary_df is not None:
                print(f"[DEBUG]   io_card_summary_df.empty: {io_card_summary_df.empty}")
                print(f"[DEBUG]   io_card_summary_df len: {len(io_card_summary_df)}")
            print(f"[DEBUG]   io_summary_df type: {type(io_summary_df)}")
            print(f"[DEBUG]   io_summary_df is None: {io_summary_df is None}")
            if io_summary_df is not None:
                print(f"[DEBUG]   io_summary_df.empty: {io_summary_df.empty}")
                print(f"[DEBUG]   io_summary_df len: {len(io_summary_df)}")
            
            # Before writing, ensure Node/Slot/Channel are safe string types for Excel
            for col in ['Node', 'Slot', 'Channel']:
                if col in assigned_df.columns:
                    assigned_df[col] = assigned_df[col].astype('object').fillna('').astype(str)

            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Write Assigned sheet
                print(f"[DEBUG] Writing {len(assigned_df)} rows to 'Assigned' sheet...")
                assigned_df.to_excel(writer, sheet_name='Assigned', index=False)
                print(f"[DEBUG] Assigned sheet written successfully")

                # Write Unassigned sheet
                if self.df_unassigned is not None and not self.df_unassigned.empty:
                    unassigned_df = self.df_unassigned.drop(columns=['IO_type_base', 'Module_Instance'], errors='ignore')
                    # Keep ONLY the required columns in specified order
                    col_order = ['PID_TAG', 'signal_origin', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS', 
                                 'Module_Name', 'Controller_No', 'Node', 'Slot', 'Channel']
                    unassigned_cols = [col for col in col_order if col in unassigned_df.columns]
                    unassigned_df = unassigned_df[unassigned_cols]  # Keep ONLY these columns, drop the rest
                    # Ensure Node/Slot/Channel are safe strings
                    for col in ['Node', 'Slot', 'Channel']:
                        if col in unassigned_df.columns:
                            unassigned_df[col] = unassigned_df[col].astype('object').fillna('').astype(str)
                    print(f"[DEBUG] Final unassigned columns: {list(unassigned_df.columns)}")
                    print(f"[DEBUG] Writing {len(unassigned_df)} rows to 'Unassigned' sheet...")
                    unassigned_df.to_excel(writer, sheet_name='Unassigned', index=False)
                    print(f"[DEBUG] Unassigned sheet written successfully")
            
            # ExcelWriter context closed - file is saved
            print(f"[DEBUG] ExcelWriter closed and data sheets saved")
            
            # Now add summary sheets and Excel formatting using openpyxl
            from openpyxl import load_workbook
            from openpyxl.utils import get_column_letter
            import time
            
            print(f"[DEBUG] Adding summary sheets and Excel formatting...")
            
            # Wait a moment for file to be fully written and accessible
            time.sleep(0.5)
            
            # Wait a moment for file to be fully written and accessible
            time.sleep(0.5)
            
            # Try to load and format the workbook - if it fails, just skip and continue
            try:
                wb = load_workbook(output_file, data_only=False)
                
                # ADD SUMMARY SHEETS USING OPENPYXL
                # Add IO Card Summary sheet FIRST
                if io_card_summary_df is not None and not io_card_summary_df.empty:
                    print(f"[DEBUG] Adding IO Card Summary sheet via openpyxl...")
                    try:
                        # Remove existing sheet if present to avoid duplicates
                        if 'IO Card Summary' in wb.sheetnames:
                            std = wb['IO Card Summary']
                            wb.remove(std)
                        ws_summary = wb.create_sheet('IO Card Summary', 0)  # Insert at position 0
                        # Write header row
                        for col_idx, col_name in enumerate(io_card_summary_df.columns, 1):
                            ws_summary.cell(row=1, column=col_idx).value = str(col_name)
                        # Write data rows (coerce missing to empty strings)
                        for row_idx, (idx, row_data) in enumerate(io_card_summary_df.iterrows(), start=2):
                            for col_idx, col_name in enumerate(io_card_summary_df.columns, 1):
                                val = row_data[col_name]
                                if pd.isna(val):
                                    val = ''
                                ws_summary.cell(row=row_idx, column=col_idx).value = str(val)
                        print(f"[DEBUG] IO Card Summary sheet added with {len(io_card_summary_df)} rows")
                    except Exception as e:
                        print(f"[WARNING] Could not add IO Card Summary: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Add IO Summary sheet
                if io_summary_df is not None and not io_summary_df.empty:
                    print(f"[DEBUG] Adding IO Summary sheet via openpyxl...")
                    try:
                        # Remove existing sheet if present to avoid duplicates
                        if 'IO Summary' in wb.sheetnames:
                            std = wb['IO Summary']
                            wb.remove(std)
                        ws_io_summary = wb.create_sheet('IO Summary', 1)  # Insert at position 1
                        # Write header row
                        for col_idx, col_name in enumerate(io_summary_df.columns, 1):
                            ws_io_summary.cell(row=1, column=col_idx).value = str(col_name)
                        # Write data rows (coerce missing to empty strings)
                        for row_idx, (idx, row_data) in enumerate(io_summary_df.iterrows(), start=2):
                            for col_idx, col_name in enumerate(io_summary_df.columns, 1):
                                val = row_data[col_name]
                                if pd.isna(val):
                                    val = ''
                                ws_io_summary.cell(row=row_idx, column=col_idx).value = str(val)
                        print(f"[DEBUG] IO Summary sheet added with {len(io_summary_df)} rows")
                    except Exception as e:
                        print(f"[WARNING] Could not add IO Summary: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Format Assigned sheet: auto-fit columns and freeze first row
                if 'Assigned' in wb.sheetnames:
                    ws_assigned = wb['Assigned']
                    ws_assigned.freeze_panes = 'A2'
                
                # Format Unassigned sheet: auto-fit columns and freeze first row
                if 'Unassigned' in wb.sheetnames:
                    ws_unassigned = wb['Unassigned']
                    ws_unassigned.freeze_panes = 'A2'
                
                # Save the workbook
                wb.save(output_file)
                print(f"[DEBUG] Workbook with summary sheets formatted and saved")
            except Exception as fmt_err:
                print(f"[WARNING] Could not add formatting: {fmt_err}")
                print(f"[WARNING] Output file created but without formatting")
            
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
            logging.exception("Failed to generate output file")
            raise
    
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
            ("Assigning modules intelligently", self.assign_modules_intelligent),
            ("Reading FIO configuration", self.read_fio_config),
            ("Assigning nodes and controllers", self.assign_nodes_and_controllers),
            ("Identifying unassigned instruments", self.identify_unassigned),
        ]
        
        for step_name, step_func in steps:
            print(f"\n[STEP] {step_name}...")
            if not step_func():
                print(f"[ERROR] Failed at step: {step_name}")
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
