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
                if module_plan['channels_used'] < module_plan['capacity']:
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
            
            if not module_assigned:
                logger.warning(f"  - Could not assign {pid_tag} to any {io_type} module (all full)")
        
        # Step 2: Distribute wired spares evenly across modules
        spares_per_module = len(spares_df) / len(self.module_allocation_plan) if self.module_allocation_plan else 0
        spare_idx = 0
        
        for module_plan in self.module_allocation_plan:
            spares_for_this_module = int(spares_per_module)
            remainder = len(spares_df) % len(self.module_allocation_plan)
            if len(self.module_allocation_plan) > 0 and module_plan == self.module_allocation_plan[remainder - 1]:
                spares_for_this_module += 1
            
            for _ in range(spares_for_this_module):
                if spare_idx >= len(spares_df):
                    break
                
                idx = spares_df.index[spare_idx]
                spare_pid = spares_df.at[idx, 'PID_TAG']
                channel = module_plan['channels_used'] + 1
                
                if channel <= module_plan['capacity']:
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
        
        channels = int(row.get('Nos of Channel', 16)) if pd.notna(row.get('Nos of Channel')) else 16
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
        
        Returns:
            List of module plan dicts
        """
        plan = []
        
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
                'capacity': channels_per_module,
                'channels_used': 0,
                'assigned_signals': [],
                'assigned_spares': []
            })
            
            # Move to next slot/node
            current_slot += 1
            if current_slot > 8:  # Max 8 slots per node
                current_slot = 1
                current_node += 1
        
        logger.info(f"[ChannelAssignmentManager] Created allocation plan with {len(plan)} modules")
        return plan
    
    def get_summary_report(self) -> str:
        """
        Generate a summary report of the allocation plan.
        
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
        report.append("MODULE ALLOCATION DETAILS:")
        report.append("-" * 100)
        
        for plan in self.module_allocation_plan:
            report.append(f"\nModule {plan['module_index'] + 1}:")
            report.append(f"  Location: Node {plan['node']}, Slot {plan['slot']}")
            report.append(f"  Type: {plan['io_type']}")
            report.append(f"  Capacity: {plan['capacity']} channels")
            report.append(f"  Assigned: {plan['channels_used']} channels")
            report.append(f"  Available: {plan['capacity'] - plan['channels_used']} channels")
            report.append(f"  Signals: {len(plan['assigned_signals'])}")
        
        report.append("\n" + "=" * 100)
        return "\n".join(report)
