"""Module calculator service."""
import math
import pandas as pd
from typing import Dict, List
from settings import MAX_NODES_PER_CONTROLLER
from domain.models.module_instance import ModuleInstance


# ========================================================================
# MODULE ALLOCATION PIPELINE - ARCHITECTURE
# ========================================================================
# PIPELINE PATTERN:
# 1. Input: rack_allocation (Dict), module_allocation_with_redundancy (Dict)
# 2. Process: create_module_allocation_dataframe()
#    ↓ Returns: Clean DataFrame with columns: Node, Slot, Module, IS_NIS, Redundancy, Channel_Capacity
# 3. Analyze: analyze_slot_allocation(allocation_df)
#    ↓ Returns: Single-row DataFrame with statistics for reporting
# 4. Output: Use DataFrame directly for exports, reports, and downstream processing
#
# Each method:
# - Takes DataFrame inputs (except where Dict input is unavoidable for legacy compatibility)
# - Returns DataFrame outputs for consistency
# - Uses standard pandas operations for filtering and transformation
# ========================================================================


class ModuleCalculator:

    def create_instances(self, template, total_channels):

        count = math.ceil(total_channels / template.usable_channels)
        modules = []

        for i in range(count):
            modules.append(ModuleInstance(template, i+1))

        return modules

    @staticmethod
    def calculate_modules_for_signal_group(
        signal_count: int,
        is_redundant: bool,
        channels_per_module: int
    ) -> int:
        """
        Calculate modules required for a signal group considering redundancy.
        
        Args:
            signal_count: Number of signals in this group
            is_redundant: True if signals are redundant (requires 2 modules per signal)
            channels_per_module: Number of usable channels per module
        
        Returns:
            Number of modules required
            
        Logic:
            - Redundant: Each signal needs 2 modules → 2 * signal_count / channels_per_module (ceiling)
            - Non-Redundant: Signals share channels → signal_count / channels_per_module (ceiling)
        """
        if signal_count <= 0 or channels_per_module <= 0:
            return 0
        
        if is_redundant:
            # Redundant signals need 2 physical modules per signal group
            # So we need 2x the channels
            total_channels_needed = signal_count * 2
            modules_required = math.ceil(total_channels_needed / channels_per_module)
            print(f"[ModuleCalculator.calculate_modules_for_signal_group]")
            print(f"  REDUNDANT: {signal_count} signals × 2 = {total_channels_needed} channels needed")
            print(f"  Modules required: {modules_required} (with {channels_per_module} ch/module)\n")
        else:
            # Non-redundant signals can share channels
            modules_required = math.ceil(signal_count / channels_per_module)
            print(f"[ModuleCalculator.calculate_modules_for_signal_group]")
            print(f"  NON-REDUNDANT: {signal_count} signals = {signal_count} channels needed")
            print(f"  Modules required: {modules_required} (with {channels_per_module} ch/module)\n")
        
        return modules_required

    @staticmethod
    def calculate_module_allocation(signal_spares_table: Dict, available_modules: pd.DataFrame, logger=None) -> pd.DataFrame:
        rows = []

        # Create normalized IO_Type mapping for available modules
        if available_modules.empty:
            return pd.DataFrame()

        # Normalize module IO_Type values (strip/upper) for robust matching
        available_modules = available_modules.copy()
        if 'IO_Type' in available_modules.columns:
            available_modules['IO_Type'] = available_modules['IO_Type'].astype(str).str.strip().str.upper()

        module_map = {}
        for _, row in available_modules.iterrows():
            io_type = row.get("IO_Type")
            if not io_type:
                continue
            if io_type not in module_map:  # Use first available for each IO_Type
                module_map[io_type] = {
                    "Module": row.get("Module", ""),
                    "Usable_Channels": row.get("Usable_Channels", 0)
                }

        # Normalize signal_spares_table keys to uppercase for matching
        normalized_signal_table = {}
        for io_type, signal_data in signal_spares_table.items():
            key = str(io_type).strip().upper()
            normalized_signal_table[key] = signal_data

        for io_type, signal_data in normalized_signal_table.items():
            if io_type not in module_map:
                unknown_module_name = f"UNKNOWN-{io_type}"
                if logger:
                    logger(
                        f"WARNING: No module mapping found for IO_Type '{io_type}' - using placeholder '{unknown_module_name}' for analysis"
                    )
                # Still include a row to allow downstream analysis, even if module is unknown
                rows.append({
                    "IO_Type": io_type,
                    "Module": unknown_module_name,
                    "IS-Red_Modules": 0,
                    "IS-NonRed_Modules": 0,
                    "NIS-Red_Modules": 0,
                    "NIS-NonRed_Modules": 0,
                    "Total_Modules": 0
                })
                continue

            module_info = module_map[io_type]
            module_name = module_info.get("Module", "")
            usable_channels = module_info.get("Usable_Channels", 0)
            
            if not module_name or usable_channels <= 0:
                unknown_module_name = f"UNKNOWN-{io_type}"
                if logger:
                    logger(
                        f"WARNING: Module mapping for IO_Type '{io_type}' is invalid (Module='{module_name}', Usable_Channels={usable_channels}); using placeholder '{unknown_module_name}'"
                    )
                rows.append({
                    "IO_Type": io_type,
                    "Module": unknown_module_name,
                    "IS-Red_Modules": 0,
                    "IS-NonRed_Modules": 0,
                    "NIS-Red_Modules": 0,
                    "NIS-NonRed_Modules": 0,
                    "Total_Modules": 0
                })
                continue
            
            is_red = math.ceil((signal_data.get("IS-Red", 0) + signal_data.get("IS-Red Spares", 0)) / usable_channels) if (signal_data.get("IS-Red", 0) + signal_data.get("IS-Red Spares", 0)) > 0 else 0
            is_nonred = math.ceil((signal_data.get("IS-NonRed", 0) + signal_data.get("IS-NonRed Spares", 0)) / usable_channels) if (signal_data.get("IS-NonRed", 0) + signal_data.get("IS-NonRed Spares", 0)) > 0 else 0
            nis_red = math.ceil((signal_data.get("NIS-Red", 0) + signal_data.get("NIS-Red Spares", 0)) / usable_channels) if (signal_data.get("NIS-Red", 0) + signal_data.get("NIS-Red Spares", 0)) > 0 else 0
            nis_nonred = math.ceil((signal_data.get("NIS-NonRed", 0) + signal_data.get("NIS-NonRed Spares", 0)) / usable_channels) if (signal_data.get("NIS-NonRed", 0) + signal_data.get("NIS-NonRed Spares", 0)) > 0 else 0
            
            rows.append({
                "IO_Type": io_type,
                "Module": module_name,
                "IS-Red_Modules": is_red,
                "IS-NonRed_Modules": is_nonred,
                "NIS-Red_Modules": nis_red,
                "NIS-NonRed_Modules": nis_nonred,
                "Total_Modules": is_red + is_nonred + nis_red + nis_nonred
            })

        allocation_df = pd.DataFrame(rows)

        # Diagnostics: warn if we had expected IO types but no allocation rows were generated
        if logger and normalized_signal_table:
            expected = set(normalized_signal_table.keys())
            actual = set(allocation_df["IO_Type"].astype(str).str.upper().unique())
            missing = expected - actual
            if missing:
                logger(f"WARNING: Expected IO types {sorted(missing)} in allocation but none were generated.")

            # Warn when DO has redundancy but ended with zero modules
            if "DO" in expected:
                do_row = allocation_df[allocation_df["IO_Type"].astype(str).str.upper() == "DO"]
                if not do_row.empty:
                    do_row = do_row.iloc[0]
                    has_red_signals = (normalized_signal_table.get("DO", {}).get("IS-Red", 0) > 0 or
                                       normalized_signal_table.get("DO", {}).get("NIS-Red", 0) > 0)
                    if has_red_signals and do_row.get("Total_Modules", 0) == 0:
                        logger("WARNING: DO has redundant signals but module allocation count is 0; check module catalog / usable channel values.")

        return allocation_df

    @staticmethod
    def apply_redundancy_doubling(allocation_df: pd.DataFrame) -> pd.DataFrame:
        df = allocation_df.copy()
        df["IS-Red_Modules"] = df["IS-Red_Modules"] * 2
        df["NIS-Red_Modules"] = df["NIS-Red_Modules"] * 2
        df["Total_Modules"] = df[["IS-Red_Modules", "IS-NonRed_Modules", "NIS-Red_Modules", "NIS-NonRed_Modules"]].sum(axis=1)
        return df

    @staticmethod
    def calculate_module_summary(before_df: pd.DataFrame, after_df: pd.DataFrame) -> pd.DataFrame:
        summary = after_df[["IO_Type", "Module"]].copy()
        summary["Single_Modules"] = before_df["IS-NonRed_Modules"] + before_df["NIS-NonRed_Modules"]
        summary["Dual_Red_Modules"] = before_df["IS-Red_Modules"] + before_df["NIS-Red_Modules"]
        summary["Total_FIO_Modules"] = after_df["Total_Modules"]
        return summary

    @staticmethod
    def build_allocation_category_map(allocation_df: pd.DataFrame) -> Dict:
        """Build category map from allocation DataFrame with critical order: NonRed first, then Red."""
        module_category_list = {}
        
        for _, row in allocation_df.iterrows():
            module_name = row.get("Module", "")
            if not module_name:
                continue
            
            if module_name not in module_category_list:
                module_category_list[module_name] = []
            
            # CRITICAL ORDER: NonRed first (Single modules), then Red (Dual modules)
            is_nonred = row.get("IS-NonRed_Modules", 0)
            nis_nonred = row.get("NIS-NonRed_Modules", 0)
            is_red = row.get("IS-Red_Modules", 0)
            nis_red = row.get("NIS-Red_Modules", 0)
            
            module_category_list[module_name].extend(["IS-NonRed"] * is_nonred)
            module_category_list[module_name].extend(["NIS-NonRed"] * nis_nonred)
            module_category_list[module_name].extend(["IS-Red"] * is_red)
            module_category_list[module_name].extend(["NIS-Red"] * nis_red)
        
        return module_category_list

    @staticmethod
    def create_module_allocation_dataframe(
        rack_allocation: Dict,
        module_allocation_with_redundancy: pd.DataFrame,
        available_modules: pd.DataFrame = None,
        iom_slots_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Create comprehensive Module Allocation DataFrame - single source of truth for module placement.
        
        Combines rack allocation with signal categories and output requirements in one clean dataframe.
        
        Final columns (ready for downstream use):
        - Node, Slot, Module: Module placement identification
        - IS_NIS: 'IS' or 'NIS' - whether module supports IS or NIS signals
        - Redundancy: 'Yes' or 'No' - whether module supports redundant signals
        - Channel_Capacity: Usable channels per module
        
        Args:
            rack_allocation: Dict[Node-X][Slot-Y] = Module name from RackAllocator
            module_allocation_with_redundancy: DataFrame from apply_redundancy_doubling()
            available_modules: DataFrame with Module, IO_Type, Usable_Channels columns
            iom_slots_df: IOM slots from constraints (optional, includes all if not provided)
        
        Returns:
            Clean DataFrame ready for direct use in reports and downstream processing
        """
        if rack_allocation is None or not rack_allocation:
            return pd.DataFrame()
        
        rows = []
        module_categories = ModuleCalculator.build_allocation_category_map(module_allocation_with_redundancy)
        module_assignment_counters = {m: 0 for m in module_categories.keys()}
        
        for node_key in sorted(rack_allocation.keys(), key=lambda x: int(x.split('-')[1])):
            node_num = int(node_key.split('-')[1])
            slots = rack_allocation[node_key]
            
            for slot_key in sorted(slots.keys(), key=lambda x: int(x.split('-')[1])):
                slot_num = int(slot_key.split('-')[1])
                module = slots[slot_key]
                
                if not module or module == '':
                    continue
                
                signal_category = "Unknown"
                if module in module_categories and module in module_assignment_counters:
                    if module_assignment_counters[module] < len(module_categories[module]):
                        signal_category = module_categories[module][module_assignment_counters[module]]
                    # Only increment counter if module is tracked
                    if module in module_assignment_counters:
                        module_assignment_counters[module] += 1
                
                rows.append({"Node": node_num, "Slot": slot_num, "Module": module, "Signal_Category": signal_category})
        
        result_df = pd.DataFrame(rows)
        if result_df.empty:
            return result_df
        
        if iom_slots_df is not None and not iom_slots_df.empty:
            iom_for_join = iom_slots_df[['Node', 'Slot']].copy().drop_duplicates()
            result_df = result_df.merge(iom_for_join, on=['Node', 'Slot'], how='inner')
        
        result_df['IS_NIS'] = result_df['Signal_Category'].str.extract(r'^(IS|NIS)', expand=False)
        result_df['Redundancy'] = result_df['Signal_Category'].str.extract(r'(Red|NonRed)$', expand=False).map({'Red': 'Yes', 'NonRed': 'No'})
        # Normalize IO Redundancy column if present
        if 'IO Redundancy' in result_df.columns:
            result_df['IO Redundancy'] = result_df['IO Redundancy'].astype(str).str.strip().str.lower()
            result_df['IO Redundancy'] = result_df['IO Redundancy'].apply(lambda x: 'Yes' if x in ['red', 'yes', 'redundant'] else 'No')
        # Add Channel_Capacity and IO_Type from available_modules. If not present, leave blank.
        if available_modules is not None and not available_modules.empty:
            module_channels = dict(zip(available_modules['Module'], available_modules['Usable_Channels']))
            result_df['Channel_Capacity'] = result_df['Module'].map(module_channels).fillna(0).astype(int)

            if 'IO_Type' in available_modules.columns:
                io_type_map = dict(zip(available_modules['Module'], available_modules['IO_Type']))
                result_df['IO_Type'] = result_df['Module'].map(io_type_map).fillna('')
            else:
                result_df['IO_Type'] = ''
        else:
            # No available_modules data; do not hardcode module types or capacities.
            result_df['Channel_Capacity'] = 0
            result_df['IO_Type'] = ''
        
        result_df = result_df[['Node', 'Slot', 'Module', 'IO_Type', 'IS_NIS', 'Redundancy', 'Channel_Capacity']]
        result_df = result_df.sort_values(by=['Node', 'Slot']).reset_index(drop=True)
        
        return result_df

    @staticmethod
    def analyze_category_compatibility(
        signals_df: pd.DataFrame,
        module_allocation_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Analyze which modules are available for each IS/Redundancy category 
        and what signal types are present in each category.

        Note:
            - This helper is intended as a diagnostic/visibility aid.
            - It does not affect channel assignment logic.

        Returns flattened DataFrame for easy display/filtering in service layer.

        Args:
            signals_df: Consolidated signals DataFrame (must have IS, Redundancy, Type, PID_TAG columns)
            module_allocation_df: Module allocation DataFrame with Redundancy column

        Returns:
            DataFrame with columns:
            - Category: IS-Red, IS-NonRed, NIS-Red, NIS-NonRed
            - Signal_Type: AI, DI, DO, AO
            - Expected_Module: Module(s) expected to satisfy that signal type (based on IO_Type)
            - Available: True if a matching module exists in the category, False otherwise
            - Available_Slots: Number of slots for the expected module(s) in this category
            - Total_Category_Slots: Total slots available in this category
            - Signal_Count: Number of this signal type in this category
            - Category_Signal_Total: Total signals in this category
        """
        def _normalize_redundancy(val):
            v = str(val).strip().lower()
            return 'Yes' if v in ['red', 'yes', 'redundant'] else 'No'

        # Normalize redundancy values so the analysis works regardless of Red/NonRed vs Yes/No usage
        signals_df = signals_df.copy()
        module_allocation_df = module_allocation_df.copy()
        if 'Redundancy' in signals_df.columns:
            signals_df['Redundancy'] = signals_df['Redundancy'].apply(_normalize_redundancy)
        if 'Redundancy' in module_allocation_df.columns:
            module_allocation_df['Redundancy'] = module_allocation_df['Redundancy'].apply(_normalize_redundancy)

        # If module_allocation_df includes IO_Type, use it to map signal types to available modules.
        # This avoids hard-coded module name expectations and keeps the analysis data-driven.
        io_type_to_modules = {}
        if 'IO_Type' in module_allocation_df.columns:
            for io_type, group in module_allocation_df.groupby('IO_Type'):
                io_type_to_modules[io_type] = sorted(group['Module'].dropna().unique())

        rows = []

        for is_status in ['IS', 'NIS']:
            for redundancy in ['Red', 'NonRed']:
                category = f"{is_status}-{redundancy}"
                redundancy_value = 'Yes' if redundancy == 'Red' else 'No'

                # Filter signals for this category
                category_signals = signals_df[
                    (signals_df.get('IS') == is_status) & 
                    (signals_df.get('Redundancy') == redundancy_value)
                ]

                # Get module slots available for this redundancy type
                category_slots = module_allocation_df[module_allocation_df.get('Redundancy') == redundancy_value]

                # Get module breakdown for this redundancy type
                module_breakdown = category_slots['Module'].value_counts().to_dict() if not category_slots.empty else {}
                total_category_slots = len(category_slots)

                # Get signal types in this category
                signal_types = category_signals['Type'].value_counts().to_dict() if not category_signals.empty else {}
                category_signal_total = len(category_signals)

                # Create one row per signal type (flatten the data)
                for signal_type, signal_count in signal_types.items():
                    expected_modules = io_type_to_modules.get(signal_type, [])
                    # Determine slots available for any of the expected modules
                    available_slots = sum(module_breakdown.get(m, 0) for m in expected_modules)
                    is_available = available_slots > 0

                    # Format module list for readability
                    expected_module_label = ', '.join(expected_modules) if expected_modules else 'Unknown'

                    rows.append({
                        'Category': category,
                        'Signal_Type': signal_type,
                        'Expected_Module': expected_module_label,
                        'Available': is_available,
                        'Available_Slots': available_slots,
                        'Total_Category_Slots': total_category_slots,
                        'Signal_Count': signal_count,
                        'Category_Signal_Total': category_signal_total
                    })

        # Return DataFrame with all analysis rows
        if rows:
            return pd.DataFrame(rows)
        else:
            # Return empty DataFrame with correct schema
            return pd.DataFrame(columns=[
                'Category', 'Signal_Type', 'Expected_Module', 'Available', 
                'Available_Slots', 'Total_Category_Slots', 'Signal_Count', 'Category_Signal_Total'
            ])

    @staticmethod
    def get_iom_slots_dataframe(excel_path: str) -> pd.DataFrame:
        """
        Get IOM slots from Mounting_Rule sheet.
        
        Reads Mounting_Rule and filters to only slots with Type='IOM'.
        Handles two constraint patterns:
        
        Pattern 1 (Multi-node): 
          - Node No = 1 for Node 1
          - Node No = '>=2' for Nodes 2-7
          
        Pattern 2 (Single-node):
          - Node No = 'Node 1 Only' for Node 1 only
        
        Logic: Use specific node notation if available (1 and >=2),
               otherwise fall back to 'Node 1 Only' if it exists.
        
        Args:
            excel_path: Path to Yokogawa_SIS_Constraints_Model_v3.xlsx
        
        Returns:
            DataFrame with columns: Node, Slot, Type
            Only rows where Type='IOM', with actual node numbers
        """
        try:
            mounting_rules_df = pd.read_excel(excel_path, sheet_name="Mounting_Rule")
            
            # Filter to only IOM type slots
            iom_slots = mounting_rules_df[
                mounting_rules_df['Type'].astype(str).str.upper() == 'IOM'
            ].copy()
            
            if iom_slots.empty:
                return pd.DataFrame()
            
            # Check which pattern is used in this constraints file
            node_notations = set(str(x).strip() for x in iom_slots['Node No'].unique())
            has_node_1 = '1' in node_notations
            has_gte_2 = '>=2' in node_notations
            has_node_1_only = 'Node 1 Only' in node_notations
            
            # Expand node notations to actual node numbers
            rows_list = []
            for _, row in iom_slots.iterrows():
                node_notation = str(row['Node No']).strip()
                slot = int(row['Slot'])
                slot_type = row['Type']
                
                # Skip if using wrong pattern
                # If specific pattern (1 and >=2) exists, skip 'Node 1 Only'
                if has_node_1 or has_gte_2:
                    if node_notation == 'Node 1 Only':
                        continue  # Skip this, use the specific pattern instead
                
                # Process the notation
                if node_notation == '1':
                    # Applies to Node 1
                    rows_list.append({'Node': 1, 'Slot': slot, 'Type': slot_type})
                elif node_notation == '>=2':
                    # Applies to Nodes 2..MAX_NODES_PER_CONTROLLER
                    for node_num in range(2, MAX_NODES_PER_CONTROLLER + 1):
                        rows_list.append({'Node': node_num, 'Slot': slot, 'Type': slot_type})
                elif node_notation == 'Node 1 Only':
                    # Single-node system: applies to Node 1 only
                    rows_list.append({'Node': 1, 'Slot': slot, 'Type': slot_type})
            
            # Create result DataFrame
            result_df = pd.DataFrame(rows_list)
            result_df = result_df.reset_index(drop=True)
            
            return result_df
            
        except Exception as e:
            print(f"[ModuleCalculator.get_iom_slots_dataframe] Error reading Mounting_Rule: {str(e)}")
            return pd.DataFrame()



    @staticmethod
    def analyze_slot_allocation(allocation_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze module allocation dataframe and return statistics as DataFrame.
        
        Provides summary statistics about allocated slots for reporting and display.
        
        Args:
            allocation_df: DataFrame from create_module_allocation_dataframe()
                Columns: Node, Slot, Module, IS_NIS, Redundancy, Channel_Capacity
        
        Returns:
            Single-row DataFrame with columns:
            - total_slots: Total number of allocated slots
            - is_count: Count of IS slots
            - nis_count: Count of NIS slots
            - redundancy_yes_count: Count of redundant slots
            - redundancy_no_count: Count of non-redundant slots
            - total_channel_capacity: Sum of all channel capacities
            - is_red_count: Count of IS-Red slots
            - is_nonred_count: Count of IS-NonRed slots
            - nis_red_count: Count of NIS-Red slots
            - nis_nonred_count: Count of NIS-NonRed slots
        """
        if allocation_df.empty:
            return pd.DataFrame({
                'total_slots': [0],
                'is_count': [0],
                'nis_count': [0],
                'redundancy_yes_count': [0],
                'redundancy_no_count': [0],
                'total_channel_capacity': [0],
                'is_red_count': [0],
                'is_nonred_count': [0],
                'nis_red_count': [0],
                'nis_nonred_count': [0]
            })
        
        # Count IS/NIS distribution
        is_count = len(allocation_df[allocation_df['IS_NIS'] == 'IS'])
        nis_count = len(allocation_df[allocation_df['IS_NIS'] == 'NIS'])
        
        # Count Redundancy distribution
        redundancy_yes_count = len(allocation_df[allocation_df['Redundancy'] == 'Yes'])
        redundancy_no_count = len(allocation_df[allocation_df['Redundancy'] == 'No'])
        
        # Count category combinations
        df_is = allocation_df[allocation_df['IS_NIS'] == 'IS']
        df_nis = allocation_df[allocation_df['IS_NIS'] == 'NIS']
        
        is_red_count = len(df_is[df_is['Redundancy'] == 'Yes']) if not df_is.empty else 0
        is_nonred_count = len(df_is[df_is['Redundancy'] == 'No']) if not df_is.empty else 0
        nis_red_count = len(df_nis[df_nis['Redundancy'] == 'Yes']) if not df_nis.empty else 0
        nis_nonred_count = len(df_nis[df_nis['Redundancy'] == 'No']) if not df_nis.empty else 0
        
        # Return as single-row DataFrame
        return pd.DataFrame({
            'total_slots': [len(allocation_df)],
            'is_count': [is_count],
            'nis_count': [nis_count],
            'redundancy_yes_count': [redundancy_yes_count],
            'redundancy_no_count': [redundancy_no_count],
            'total_channel_capacity': [allocation_df['Channel_Capacity'].sum()],
            'is_red_count': [is_red_count],
            'is_nonred_count': [is_nonred_count],
            'nis_red_count': [nis_red_count],
            'nis_nonred_count': [nis_nonred_count]
        })


# ========================================================================
# MODULE ALLOCATION PIPELINE - MAIN ENTRY POINT
# ========================================================================
# Usage:
#   1. allocation_df = ModuleCalculator.create_module_allocation_dataframe(
#        rack_allocation, module_allocation_with_redundancy, 
#        available_modules, iom_slots_df)
#   2. analysis = ModuleCalculator.analyze_slot_allocation(allocation_df)
#   3. Use allocation_df directly for reports/exports
# ========================================================================
