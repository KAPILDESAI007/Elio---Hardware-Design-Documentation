"""
Channel Assignment Manager
Handles intelligent, module-by-module channel assignment with even wired spare distribution.

Logic:
1. Process one module at a time (Node-1/Slot-1, then Slot-2, etc.)
2. Group signals by module type (AI, DI, DO, etc.)
3. Fill all signals of same type into one module before moving to next
4. Distribute wired spares evenly across all modules
5. Ensure each module has at least 1 empty channel (or equal distribution)
"""

import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("CloudAppLogger")


class ChannelAssignmentManager:
    """
    Intelligent channel assignment manager that processes one module at a time,
    groups signals by type, and distributes wired spares evenly.
    """
    
    def __init__(self, df_instruments: pd.DataFrame, df_hardware: pd.DataFrame):
        """
        Initialize the manager with instrument and hardware data.
        
        Args:
            df_instruments: DataFrame with signals (PID_TAG, IO_type, etc.)
            df_hardware: DataFrame with module specifications
        """
        self.df_instruments = df_instruments.copy()
        self.df_hardware = df_hardware.copy()
        
        # Analysis results
        self.module_allocation_plan = []  # List of module assignments
        self.wired_spares_per_module = 0
        self.signals_per_module = 0
        self.total_modules_needed = 0
        self.assignment_log = []
        
        logger.info(f"[ChannelAssignmentManager] Initialized with {len(df_instruments)} signals and {len(df_hardware)} hardware configs")
    
    def analyze_and_plan(self) -> Dict:
        """
        Analyze the input data and create an assignment plan.
        
        Returns:
            Dict with analysis results:
            {
                'total_signals': int,
                'total_modules': int,
                'wired_spares_per_module': int,
                'signals_per_module': int,
                'module_plan': List[Dict],
                'success': bool
            }
        """
        logger.info("[ChannelAssignmentManager] Starting analysis and planning...")
        
        # Step 1: Count total signals and wired spares
        total_signals = len(self.df_instruments)
        wired_spares_count = self._count_wired_spares()
        actual_signals = total_signals - wired_spares_count
        
        logger.info(f"  - Total items: {total_signals}")
        logger.info(f"  - Actual signals: {actual_signals}")
        logger.info(f"  - Wired spares: {wired_spares_count}")
        
        # Step 2: Group signals by IO type
        signal_groups = self._group_signals_by_type()
        logger.info(f"  - Signal groups: {list(signal_groups.keys())}")
        for io_type, count in signal_groups.items():
            logger.info(f"    * {io_type}: {count} signals")
        
        # Step 3: Determine module capacity and module count
        module_info = self._determine_module_specs()
        if not module_info:
            logger.error("[ChannelAssignmentManager] Failed to determine module specifications")
            return {'success': False, 'error': 'Cannot determine module specs'}
        
        channels_per_module = module_info['channels']
        logger.info(f"  - Channels per module: {channels_per_module}")
        
        # Step 4: Calculate modules needed
        total_items = actual_signals + wired_spares_count
        modules_needed = (total_items + channels_per_module - 1) // channels_per_module
        logger.info(f"  - Modules needed: {modules_needed} (for {total_items} items at {channels_per_module} channels/module)")
        
        # Step 5: Distribute wired spares evenly
        if modules_needed > 0 and wired_spares_count > 0:
            spares_per_module = wired_spares_count / modules_needed
            logger.info(f"  - Wired spares distribution: {spares_per_module:.2f} per module")
        else:
            spares_per_module = 0
        
        # Step 6: Create assignment plan
        plan = self._create_assignment_plan(
            signal_groups=signal_groups,
            wired_spares_count=wired_spares_count,
            modules_needed=modules_needed,
            channels_per_module=channels_per_module,
            spares_per_module=spares_per_module
        )
        
        self.module_allocation_plan = plan
        self.total_modules_needed = modules_needed
        self.wired_spares_per_module = spares_per_module
        
        result = {
            'success': True,
            'total_signals': actual_signals,
            'total_wired_spares': wired_spares_count,
            'total_modules': modules_needed,
            'channels_per_module': channels_per_module,
            'wired_spares_per_module': spares_per_module,
            'signal_groups': signal_groups,
            'module_plan': plan
        }
        
        logger.info(f"[ChannelAssignmentManager] Analysis complete. Created plan for {modules_needed} modules")
        return result
    
    def assign_channels(self, node_start: int = 1, slot_start: int = 1) -> pd.DataFrame:
        """
        Execute the assignment plan and assign channels to all signals.
        
        Args:
            node_start: Starting node number
            slot_start: Starting slot number
            
        Returns:
            DataFrame with assigned channels, or empty DataFrame if error
        """
        logger.info(f"[ChannelAssignmentManager] Assigning channels starting from Node {node_start}, Slot {slot_start}...")
        
        if not self.module_allocation_plan:
            logger.error("[ChannelAssignmentManager] No allocation plan. Call analyze_and_plan() first.")
            return pd.DataFrame()
        
        # Initialize assignment columns
        df_result = self.df_instruments.copy()
        df_result['Module_Name'] = ""
        df_result['Module_Instance'] = ""  # Add this for backward compatibility
        df_result['Node'] = 0
        df_result['Slot'] = 0
        df_result['Channel'] = 0
        df_result['Slot_P'] = 0  # Primary slot
        df_result['Slot_R'] = pd.NA  # Redundant slot (if any)
        df_result['Redundancy_Flag'] = 'No'
        
        current_node = node_start
        current_slot = slot_start
        current_channel = 1
        module_index = 0
        assignments_made = 0
        
        # Separate signals and wired spares
        signal_mask = ~self.df_instruments['PID_TAG'].astype(str).str.contains('SPARE|spare', case=False, na=False)
        signals_df = self.df_instruments[signal_mask].copy()
        spares_df = self.df_instruments[~signal_mask].copy()
        
        # Filter out SOFT signals - they should not be assigned to channels
        soft_mask = signals_df['IO_type_base'].astype(str).str.contains('SOFT|soft|SOFTWARE|software', case=False, na=False)
        non_soft_signals = signals_df[~soft_mask].copy()
        soft_signals = signals_df[soft_mask].copy()
        
        logger.info(f"  - Processing {len(non_soft_signals)} hardware signals and {len(spares_df)} wired spares")
        logger.info(f"  - Skipping {len(soft_signals)} SOFT signals (not assigned to channels)")
        
        # Step 1: Assign signals to modules
        for idx, row in non_soft_signals.iterrows():
            io_type = str(row.get('IO_type_base', 'UNKNOWN')).upper().strip()
            pid_tag = str(row.get('PID_TAG', 'UNKNOWN')).strip()
            
            # Find matching module in plan
            matching_modules = [m for m in self.module_allocation_plan if m['io_type'] == io_type]
            
            if not matching_modules:
                logger.warning(f"  - No module plan found for {io_type}, skipping {pid_tag}")
                continue
            
            # Use the first matching module that still has capacity
            module_assigned = False
            for module_plan in matching_modules:
                # Check both capacity and usable_channels constraint (requirement #10)
                usable_limit = module_plan.get('usable_channels_limit', module_plan['capacity'])
                
                # CRITICAL: Check BOTH capacity AND Usable_Channels limit
                if module_plan['channels_used'] < module_plan['capacity'] and module_plan['channels_used'] < usable_limit:
                    # Assign to this module
                    channel = module_plan['channels_used'] + 1
                    module_name = module_plan['module_name']
                    
                    # Create Module_Instance by appending instance number
                    # Instance is based on node and slot (e.g., "AI_1", "AI_2")
                    instance_num = module_plan['module_index'] + 1
                    module_instance = f"{module_name}_{instance_num}"
                    
                    df_result.at[idx, 'Module_Name'] = module_name
                    df_result.at[idx, 'Module_Instance'] = module_instance
                    df_result.at[idx, 'Node'] = module_plan['node']
                    df_result.at[idx, 'Slot'] = module_plan['slot']
                    df_result.at[idx, 'Slot_P'] = module_plan['slot']
                    df_result.at[idx, 'Channel'] = channel
                    
                    # Update module tracking
                    module_plan['channels_used'] += 1
                    module_plan['assigned_signals'].append(pid_tag)
                    
                    assignments_made += 1
                    module_assigned = True
                    logger.debug(f"  - Assigned {pid_tag} to {module_instance} N{module_plan['node']}S{module_plan['slot']} CH{channel}")
                    break
                else:
                    logger.debug(f"  - Skipping module for {pid_tag}: used={module_plan['channels_used']}, capacity={module_plan['capacity']}, usable_limit={usable_limit}")
            
            if not module_assigned:
                logger.warning(f"  - Could not assign {pid_tag} to any {io_type} module (all full)")
        
        # Step 2: Distribute wired spares evenly across modules
        # FIX: Use proper distribution calculation - don't truncate, distribute remainder
        num_modules = len(self.module_allocation_plan)
        num_spares = len(spares_df)
        spare_idx = 0
        
        if num_modules > 0:
            spares_base_per_module = num_spares // num_modules  # Integer division
            spares_remainder = num_spares % num_modules         # Remainder to distribute
        else:
            spares_base_per_module = 0
            spares_remainder = 0
        
        for module_idx, module_plan in enumerate(self.module_allocation_plan):
            # Distribute remainder spares to first N modules
            spares_for_this_module = spares_base_per_module
            if module_idx < spares_remainder:
                spares_for_this_module += 1
            
            logger.debug(f"  [Module {module_idx}] Assigning {spares_for_this_module} spares (base={spares_base_per_module}, remainder_idx={module_idx}/{spares_remainder})")
            
            for spare_count in range(spares_for_this_module):
                if spare_idx >= len(spares_df):
                    break
                
                idx = spares_df.index[spare_idx]
                spare_pid = spares_df.at[idx, 'PID_TAG']
                channel = module_plan['channels_used'] + 1
                
                # Check Usable_Channels constraint per requirement #10
                if channel <= module_plan['capacity'] and channel <= module_plan.get('usable_channels_limit', module_plan['capacity']):
                    module_name = module_plan['module_name']
                    instance_num = module_plan['module_index'] + 1
                    module_instance = f"{module_name}_{instance_num}"
                    
                    df_result.at[idx, 'Module_Name'] = module_name
                    df_result.at[idx, 'Module_Instance'] = module_instance
                    df_result.at[idx, 'Node'] = module_plan['node']
                    df_result.at[idx, 'Slot'] = module_plan['slot']
                    df_result.at[idx, 'Slot_P'] = module_plan['slot']
                    df_result.at[idx, 'Channel'] = channel
                    
                    module_plan['channels_used'] += 1
                    assignments_made += 1
                    logger.debug(f"  - Assigned wired spare {spare_pid} to N{module_plan['node']}S{module_plan['slot']} CH{channel}")
                else:
                    logger.warning(f"  - Cannot assign wired spare {spare_pid}: module at capacity (CH{channel} > limit {module_plan.get('usable_channels_limit', 'N/A')})")
                
                spare_idx += 1
        
        logger.info(f"[ChannelAssignmentManager] Channel assignment complete. {assignments_made} assignments made")
        return df_result
    
    def _count_wired_spares(self) -> int:
        """Count items marked as wired spares."""
        if 'PID_TAG' not in self.df_instruments.columns:
            return 0
        
        wired_spares = self.df_instruments['PID_TAG'].astype(str).str.contains(
            'SPARE|spare|Spare', 
            case=False, 
            na=False
        )
        count = wired_spares.sum()
        return int(count)
    
    def _group_signals_by_type(self) -> Dict[str, int]:
        """
        Group signals by IO type.
        
        Returns:
            Dict mapping IO_type to count
        """
        # Filter out wired spares
        signal_mask = ~self.df_instruments['PID_TAG'].astype(str).str.contains('SPARE|spare', case=False, na=False)
        signals = self.df_instruments[signal_mask]
        
        if 'IO_type_base' not in signals.columns:
            logger.warning("[ChannelAssignmentManager] IO_type_base column not found")
            return {}
        
        groups = signals.groupby('IO_type_base').size().to_dict()
        return {k: int(v) for k, v in groups.items()}
    
    def _determine_module_specs(self) -> Optional[Dict]:
        """
        Determine module specifications from hardware config.
        
        Returns:
            Dict with 'channels', 'module_name', etc. or None
        """
        if self.df_hardware.empty:
            logger.warning("[ChannelAssignmentManager] Hardware config is empty")
            return None
        
        # Use first available module specs
        row = self.df_hardware.iloc[0]
        
        # Per design requirement #10: Use Usable_Channels for constraint validation
        # Usable_Channels is the maximum allowed channels per module (from IO_Module_Catalog)
        if 'Usable_Channels' in row.index and pd.notna(row['Usable_Channels']):
            channels = int(row['Usable_Channels'])
            logger.info(f"[ChannelAssignmentManager] Using Usable_Channels constraint: {channels} channels/module")
        elif 'Nos of Channel' in row.index and pd.notna(row['Nos of Channel']):
            channels = int(row['Nos of Channel'])
            logger.warning(f"[ChannelAssignmentManager] Usable_Channels not found, using Nos of Channel: {channels}")
        else:
            channels = 16  # Default fallback
            logger.warning(f"[ChannelAssignmentManager] No channel info found, using default: {channels}")
        
        module_name = str(row.get('Module', 'FIO')).strip()
        
        return {
            'channels': channels,
            'module_name': module_name,
            'module_row': row
        }
    
    def _create_assignment_plan(
        self,
        signal_groups: Dict[str, int],
        wired_spares_count: int,
        modules_needed: int,
        channels_per_module: int,
        spares_per_module: float
    ) -> List[Dict]:
        """
        Create a module allocation plan.
        Per design requirement #10: Validate against Usable_Channels constraint
        
        Returns:
            List of module plan dicts
        """
        plan = []
        
        # Get Usable_Channels limit per design requirement #10
        usable_channels_limit = channels_per_module
        if not self.df_hardware.empty and 'Usable_Channels' in self.df_hardware.columns:
            hw_row = self.df_hardware.iloc[0]
            if pd.notna(hw_row.get('Usable_Channels')):
                usable_channels_limit = int(hw_row['Usable_Channels'])
                logger.info(f"[ChannelAssignmentManager] Usable_Channels constraint set to {usable_channels_limit}")
        
        # Use the more restrictive limit (usable vs capacity)
        effective_capacity = min(channels_per_module, usable_channels_limit)
        
        # Determine which module types we have
        module_types = signal_groups.keys()
        
        current_node = 1
        current_slot = 1
        module_number = 0
        
        # Create one plan entry per module needed
        for i in range(modules_needed):
            # Distribute IO types across modules round-robin
            io_type = list(module_types)[i % len(module_types)] if module_types else 'UNKNOWN'
            
            plan.append({
                'module_index': i,
                'node': current_node,
                'slot': current_slot,
                'io_type': io_type,
                'module_name': self.df_hardware.iloc[0].get('Module', 'FIO') if not self.df_hardware.empty else 'FIO',
                'capacity': effective_capacity,  # Use effective capacity with Usable_Channels constraint
                'usable_channels_limit': usable_channels_limit,  # Store limit for reference
                'channels_used': 0,
                'assigned_signals': [],
                'assigned_spares': []
            })
            
            # Move to next slot/node
            current_slot += 1
            if current_slot > 8:  # Max 8 slots per node
                current_slot = 1
                current_node += 1
        
        logger.info(f"[ChannelAssignmentManager] Created allocation plan with {len(plan)} modules (effective capacity: {effective_capacity})")
        return plan
    
    def get_summary_report(self) -> str:
        """
        Generate a summary report of the allocation plan.
        Per design requirement #10: Display Usable_Channels constraint validation.
        
        Returns:
            Formatted string with summary
        """
        report = []
        report.append("\n" + "=" * 100)
        report.append("CHANNEL ASSIGNMENT PLAN SUMMARY")
        report.append("=" * 100)
        
        if not self.module_allocation_plan:
            report.append("No allocation plan created yet. Call analyze_and_plan() first.")
            return "\n".join(report)
        
        report.append(f"\nTotal Modules: {len(self.module_allocation_plan)}")
        report.append(f"Wired Spares per Module: {self.wired_spares_per_module:.2f}")
        
        report.append("\n" + "-" * 100)
        report.append("MODULE ALLOCATION DETAILS (with Usable_Channels constraint per Requirement #10):")
        report.append("-" * 100)
        
        constraint_violations = 0
        for plan in self.module_allocation_plan:
            usable_limit = plan.get('usable_channels_limit', plan['capacity'])
            violation = plan['channels_used'] > usable_limit
            violation_marker = " ⚠ CONSTRAINT VIOLATED" if violation else ""
            
            report.append(f"\nModule {plan['module_index'] + 1}:")
            report.append(f"  Location: Node {plan['node']}, Slot {plan['slot']}")
            report.append(f"  Type: {plan['io_type']}")
            report.append(f"  Capacity: {plan['capacity']} channels")
            report.append(f"  Usable_Channels Limit: {usable_limit} channels")
            report.append(f"  Assigned: {plan['channels_used']} channels{violation_marker}")
            report.append(f"  Available: {max(0, plan['capacity'] - plan['channels_used'])} channels")
            report.append(f"  Signals: {len(plan['assigned_signals'])}")
            
            if violation:
                constraint_violations += 1
        
        if constraint_violations > 0:
            report.append("\n" + "!" * 100)
            report.append(f"⚠ WARNING: {constraint_violations} module(s) exceed Usable_Channels constraint!")
            report.append("!" * 100)
        else:
            report.append("\n" + "✓" * 50)
            report.append("✓ All modules comply with Usable_Channels constraint (Requirement #10)")
            report.append("✓" * 50)
        
        report.append("\n" + "=" * 100)
        return "\n".join(report)


class ChannelDistributionManager:
    """
    New channel assignment manager using system constraints approach.
    
    Distributes signals, wired spares, and blank channels equally across modules
    for each IO type based on module capacity and requirements from SystemConstraints.
    
    Flow:
    1. Calculate total available channels (modules_required × channels_per_module)
    2. Distribute signals + wired spares + blank channels equally per module
    3. Create channel assignment plan showing:
       - Module instance
       - Channels allocated per type (signal, spare, blank)
       - Channel ranges
    """
    
    def __init__(self, logger=None):
        """
        Initialize the channel distribution manager.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.distribution_plan = {}  # Dict[io_type, distribution details]
        self.module_channel_map = {}  # Dict[(io_type, module_idx), channel assignments]
    
    
    def calculate_total_available_channels(self, module_requirements: Dict[str, dict]) -> Dict[str, dict]:
        """
        Calculate total available channels for each IO type.
        
        Total available = modules_required × usable_channels_per_module
        
        Args:
            module_requirements (Dict[str, dict]): Output from calculate_modules_required()
                Expected keys per IO_type: module_name, usable_channels_per_module, modules_required
        
        Returns:
            Dict[str, dict]: For each IO_type contains:
            {
                'modules_required': int,
                'usable_channels_per_module': int,
                'total_available_channels': int,
                'module_name': str
            }
        """
        try:
            available_channels = {}
            
            for io_type, req in module_requirements.items():
                total_channels = req['modules_required'] * req['usable_channels_per_module']
                
                available_channels[io_type] = {
                    'modules_required': req['modules_required'],
                    'usable_channels_per_module': req['usable_channels_per_module'],
                    'total_available_channels': total_channels,
                    'module_name': req['module_name']
                }
                
                self.logger.info(
                    f"Available channels for {io_type}: {req['modules_required']} modules × "
                    f"{req['usable_channels_per_module']} ch/module = {total_channels} channels"
                )
            
            return available_channels
        except Exception as e:
            self.logger.error(f"Error calculating available channels: {e}")
            raise
    
    
    def distribute_channels_equally(self, 
                                   signal_counts: Dict[str, int],
                                   wired_spares: Dict[str, int],
                                   module_requirements: Dict[str, dict]) -> Dict[str, dict]:
        """
        Distribute signals, wired spares, and blank channels equally across modules per IO type.
        
        For each IO type:
        1. Calculate total items = signals + wired spares
        2. Distribute across modules: each module gets equal share (with remainder handling)
        3. Calculate blank channels = total_available - (signals + spares)
        4. Return distribution details per module
        
        CRITICAL: Ensure total_assigned never exceeds module_capacity
        
        Args:
            signal_counts (Dict[str, int]): Signals per IO type (from InputDataAnalyzer)
            wired_spares (Dict[str, int]): Wired spares per IO type (from InputDataAnalyzer)
            module_requirements (Dict[str, dict]): Module capacity info (from SystemConstraints)
        
        Returns:
            Dict[str, dict]: Distribution plan per IO_type
            {
                'io_type': {
                    'signals': int,
                    'wired_spares': int,
                    'total_items': int,
                    'modules_required': int,
                    'channels_per_module': int,
                    'total_available_channels': int,
                    'blank_channels': int,
                    'per_module_distribution': {...},
                    'module_specs': [...]  # List of per-module assignments
                }
            }
        """
        try:
            distribution_plan = {}
            
            for io_type in module_requirements.keys():
                signals = signal_counts.get(io_type, 0)
                spares = wired_spares.get(io_type, 0)
                req = module_requirements[io_type]
                
                modules_required = req['modules_required']
                channels_per_module = req['usable_channels_per_module']
                total_available = modules_required * channels_per_module
                
                total_items = signals + spares
                blank_channels = max(0, total_available - total_items)
                
                # Calculate equal distribution of TOTAL items (not separate for signals/spares)
                base_items_per_module = total_items // modules_required if modules_required > 0 else 0
                remainder_items = total_items % modules_required if modules_required > 0 else 0
                
                # CRITICAL FIX: Ensure module capacity is never exceeded
                # Cap base_items to module capacity
                base_items_per_module = min(base_items_per_module, channels_per_module)
                
                # Distribute signals and spares proportionally within each module's allocation
                module_specs = []
                signal_idx = 0
                spare_idx = 0
                
                for mod_idx in range(modules_required):
                    # Determine total allocation for this module
                    module_total = base_items_per_module
                    if mod_idx < remainder_items:
                        module_total += 1
                    
                    # Ensure never exceeds capacity
                    module_total = min(module_total, channels_per_module)
                    
                    # Now distribute signals and spares within this total
                    # Distribute remaining signals first, then spares
                    remaining_signals = signals - signal_idx
                    remaining_spares = spares - spare_idx
                    
                    # Allocate available slots to signals (priority)
                    module_signals = min(remaining_signals, module_total)
                    module_spares = min(remaining_spares, module_total - module_signals)
                    module_items = module_signals + module_spares
                    module_blanks = max(0, channels_per_module - module_items)
                    
                    signal_idx += module_signals
                    spare_idx += module_spares
                    
                    module_specs.append({
                        'module_instance': f"{req['module_name']}_{mod_idx + 1}",
                        'module_index': mod_idx,
                        'signals': module_signals,
                        'wired_spares': module_spares,
                        'blank_channels': module_blanks,
                        'total_items': module_items,
                        'channel_range': f"1-{channels_per_module}",
                        'capacity': channels_per_module
                    })
                
                distribution_plan[io_type] = {
                    'signals': signals,
                    'wired_spares': spares,
                    'total_items': total_items,
                    'modules_required': modules_required,
                    'channels_per_module': channels_per_module,
                    'total_available_channels': total_available,
                    'blank_channels': blank_channels,
                    'module_name': req['module_name'],
                    'per_module_distribution': {
                        'base_items_per_module': base_items_per_module,
                        'remainder_items': remainder_items,
                        'first_n_modules_get_extra': remainder_items,
                        'signals_per_module': f"~{signals // modules_required if modules_required > 0 else 0}",
                        'spares_per_module': f"~{spares // modules_required if modules_required > 0 else 0}",
                        'blank_per_module': f"~{channels_per_module - base_items_per_module}"
                    },
                    'module_specs': module_specs
                }
                
                self.logger.info(
                    f"Distribution for {io_type}: {signals} signals + {spares} spares = {total_items} items → "
                    f"{modules_required} modules × {channels_per_module} ch = {total_available} available, "
                    f"{blank_channels} blank channels"
                )
                
            self.distribution_plan = distribution_plan
            return distribution_plan
            
        except Exception as e:
            self.logger.error(f"Error distributing channels: {e}")
            raise
    
    
    def create_channel_assignment_table(self, distribution_plan: Dict[str, dict], 
                                       mounting_table: pd.DataFrame = None) -> pd.DataFrame:
        """
        Create a detailed channel assignment table showing channel allocation per module.
        
        Table structure:
        - Rows: One row per module instance per IO type
        - Columns: Module name, Module Index, Signals, Wired_Spares, Blank_Channels, Total, 
                   Capacity, Utilization %, Channel_Range, Node, Slot (if mounting_table provided)
        
        Args:
            distribution_plan (Dict[str, dict]): Output from distribute_channels_equally()
            mounting_table (pd.DataFrame, optional): From build_mounting_table() to add Node/Slot info
        
        Returns:
            pd.DataFrame: Channel assignment table
        """
        try:
            table_rows = []
            
            for io_type in sorted(distribution_plan.keys()):
                plan = distribution_plan[io_type]
                modules = plan['module_specs']
                
                for module_spec in modules:
                    row = {
                        'IO_Type': io_type,
                        'Module_Name': module_spec['module_instance'],
                        'Module_Index': module_spec['module_index'],
                        'Signals': module_spec['signals'],
                        'Wired_Spares': module_spec['wired_spares'],
                        'Blank_Channels': module_spec['blank_channels'],
                        'Total_Assigned': module_spec['total_items'],
                        'Module_Capacity': module_spec['capacity'],
                        'Utilization_%': round(
                            (module_spec['total_items'] / module_spec['capacity'] * 100) 
                            if module_spec['capacity'] > 0 else 0, 
                            1
                        ),
                        'Channel_Range': f"1-{module_spec['capacity']}",
                        'Status': 'Full' if module_spec['blank_channels'] == 0 else f"{module_spec['blank_channels']} spare"
                    }
                    
                    # Add Node/Slot if mounting table provided
                    if mounting_table is not None:
                        # Try to find module location in mounting table
                        module_name = module_spec['module_instance']
                        found_location = None
                        
                        for node_idx, node_name in enumerate(mounting_table.index):
                            for slot_idx, slot_name in enumerate(mounting_table.columns):
                                cell_value = mounting_table.loc[node_name, slot_name]
                                if cell_value == module_name:
                                    # Extract node and slot numbers
                                    node_num = int(node_name.split('_')[1])
                                    slot_num = int(slot_name.split('_')[1])
                                    found_location = (node_num, slot_num)
                                    break
                            if found_location:
                                break
                        
                        if found_location:
                            row['Node'] = found_location[0]
                            row['Slot'] = found_location[1]
                        else:
                            row['Node'] = 'N/A'
                            row['Slot'] = 'N/A'
                    
                    table_rows.append(row)
            
            df_assignment = pd.DataFrame(table_rows)
            
            self.logger.info(f"Created channel assignment table with {len(df_assignment)} module entries")
            return df_assignment
            
        except Exception as e:
            self.logger.error(f"Error creating channel assignment table: {e}")
            raise
    
    
    def get_distribution_summary(self, distribution_plan: Dict[str, dict]) -> str:
        """
        Generate a formatted summary of the channel distribution plan.
        
        Args:
            distribution_plan (Dict[str, dict]): Output from distribute_channels_equally()
        
        Returns:
            str: Formatted summary report
        """
        report = []
        report.append("\n" + "=" * 100)
        report.append("CHANNEL DISTRIBUTION SUMMARY")
        report.append("=" * 100)
        
        for io_type in sorted(distribution_plan.keys()):
            plan = distribution_plan[io_type]
            
            report.append(f"\n{io_type} ({plan['module_name']}):")
            report.append("-" * 100)
            report.append(f"  Total Signals: {plan['signals']}")
            report.append(f"  Total Wired Spares: {plan['wired_spares']}")
            report.append(f"  Total Items: {plan['total_items']}")
            report.append(f"  Modules Required: {plan['modules_required']}")
            report.append(f"  Channels per Module: {plan['channels_per_module']}")
            report.append(f"  Total Available Channels: {plan['total_available_channels']}")
            report.append(f"  Blank Channels: {plan['blank_channels']}")
            
            dist = plan['per_module_distribution']
            report.append(f"\n  Per Module Distribution:")
            report.append(f"    - Base items per module: {dist['base_items_per_module']}")
            report.append(f"    - Remainder items: {dist['remainder_items']}")
            report.append(f"    - First {dist['first_n_modules_get_extra']} modules get +1 item")
            report.append(f"    - Signals per module (avg): {dist['signals_per_module']}")
            report.append(f"    - Spares per module (avg): {dist['spares_per_module']}")
            report.append(f"    - Blank per module (avg): {dist['blank_per_module']}")
            
            report.append(f"\n  Module Details (first 5 shown):")
            for i, spec in enumerate(plan['module_specs'][:5]):
                report.append(
                    f"    {spec['module_instance']}: "
                    f"{spec['signals']} signals + {spec['wired_spares']} spares + {spec['blank_channels']} blank = "
                    f"{spec['total_items']}/{spec['capacity']}"
                )
            if len(plan['module_specs']) > 5:
                report.append(f"    ... and {len(plan['module_specs']) - 5} more modules")
        
        report.append("\n" + "=" * 100)
        return "\n".join(report)
    
    
    def assign_signals_to_channels(self, 
                                   df_instruments: pd.DataFrame,
                                   signal_counts: Dict[str, int],
                                   distribution_plan: Dict[str, dict],
                                   mounting_table: pd.DataFrame = None) -> pd.DataFrame:
        """
        Assign individual signals to specific channels in modules.
        
        Args:
            df_instruments: DataFrame with signal/instrument data
            signal_counts: Signal counts per IO type
            distribution_plan: Output from distribute_channels_equally()
            mounting_table: Optional mounting table from SystemConstraints
        
        Returns:
            DataFrame with signal-to-channel assignments
        """
        try:
            assignment_rows = []
            signal_indices = {io_type: 0 for io_type in signal_counts.keys()}
            
            # Separate signals by IO type
            for io_type in sorted(signal_counts.keys()):
                if signal_counts.get(io_type, 0) == 0:
                    continue
                
                # Filter signals for this IO type
                type_mask = df_instruments['IO_type_base'].astype(str).str.upper() == io_type
                type_signals = df_instruments[type_mask].copy().reset_index(drop=True)
                
                if len(type_signals) == 0:
                    continue
                
                plan = distribution_plan[io_type]
                modules = plan['module_specs']
                
                signal_idx = 0
                for module_spec in modules:
                    module_name = module_spec['module_instance']
                    module_signals = module_spec['signals']
                    
                    # Get Node and Slot from mounting table if available
                    node = 'N/A'
                    slot = 'N/A'
                    if mounting_table is not None:
                        for node_name in mounting_table.index:
                            for slot_name in mounting_table.columns:
                                cell = mounting_table.loc[node_name, slot_name]
                                if cell == module_name:
                                    node = int(node_name.split('_')[1])
                                    slot = int(slot_name.split('_')[1])
                                    break
                    
                    # Assign signals to channels for this module
                    for ch in range(1, module_signals + 1):
                        if signal_idx >= len(type_signals):
                            break
                        
                        signal_row = type_signals.iloc[signal_idx]
                        assignment_rows.append({
                            'PID_TAG': signal_row.get('PID_TAG', ''),
                            'Description': signal_row.get('Description', ''),
                            'IO_Type': io_type,
                            'Module_Name': module_name,
                            'Module_Index': module_spec['module_index'],
                            'Channel': ch,
                            'Node': node,
                            'Slot': slot,
                            'Signal_Type': 'Signal',
                            'Utilization': 'Active'
                        })
                        signal_idx += 1
            
            df_assignment = pd.DataFrame(assignment_rows)
            self.logger.info(f"Assigned {len(df_assignment)} signals to channels")
            return df_assignment
            
        except Exception as e:
            self.logger.error(f"Error assigning signals to channels: {e}")
            raise
