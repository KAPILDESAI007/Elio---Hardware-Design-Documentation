"""Channel Allocator - Maps signals to specific module slots and channels."""

import pandas as pd
from typing import Dict, List, Tuple


class ChannelAllocator:
    """Allocates I/O signals to hardware module channels with redundancy handling."""

    def __init__(self):
        """Initialize channel allocator state."""
        self.processed_signals = set()
        self.slot_channel_usage = {}  # Track used channels per (node, slot)

    def allocate_signals_to_channels(
        self,
        signals_df: pd.DataFrame,
        module_allocation_df: pd.DataFrame,
        available_modules,
        logger_callback=None
    ) -> pd.DataFrame:
        """
        Allocate signals to module channels using two DataFrames.
        
        Flow:
        1. df1 (signals_df): Signal metadata (PID_TAG, Type, IS, Redundancy)
        2. df2 (module_allocation_df): Module allocation table (Node, Slot, Module, Redundancy, IS_NIS, Channel_Capacity)
        3. Filter signals by (IS, Redundancy, Type) and allocate to compatible modules
        4. Fill all 16 channels per slot before moving to next slot

        Args:
            signals_df: DataFrame with signal data (consolidated signals with IS, Redundancy, Type columns)
            module_allocation_df: DataFrame with module allocation metadata
            available_modules: DataFrame or list of available module specifications
            logger_callback: Optional logging callback

        Returns:
            Updated DataFrame with Node, Slot, Channel columns filled
        """
        if logger_callback:
            logger_callback("Initializing channel allocation with module allocation DataFrame...")

        # Create working copy
        result_df = signals_df.copy()
        result_df['Node'] = None
        result_df['Slot'] = None
        result_df['Channel'] = None
        result_df['Module'] = None

        if logger_callback:
            logger_callback(f"DEBUG: Starting allocation for {len(signals_df)} signals across {len(module_allocation_df)} allocated slots")
            logger_callback(f"DEBUG: Module Allocation DataFrame structure:")
            logger_callback(f"  Columns: {module_allocation_df.columns.tolist()}")
            logger_callback(f"  Redundancy values: {module_allocation_df['Redundancy'].unique().tolist() if 'Redundancy' in module_allocation_df.columns else 'N/A'}")
            logger_callback(f"  IS_NIS values: {module_allocation_df['IS_NIS'].unique().tolist() if 'IS_NIS' in module_allocation_df.columns else 'N/A'}")
            logger_callback(f"  Module types: {module_allocation_df['Module'].unique().tolist() if 'Module' in module_allocation_df.columns else 'N/A'}")

        # Allocate signals in priority order: IS-Red, IS-NonRed, NIS-Red, NIS-NonRed
        allocation_order = [
            ('IS', 'Red'),
            ('IS', 'NonRed'),
            ('NIS', 'Red'),
            ('NIS', 'NonRed')
        ]
        
        for is_status, redundancy in allocation_order:
            self._allocate_signals_by_category(
                result_df, 
                module_allocation_df, 
                available_modules, 
                logger_callback,
                is_status=is_status,
                redundancy=redundancy
            )

        if logger_callback:
            logger_callback("Channel allocation complete.")

        return result_df

    def _allocate_signals_by_category(
        self,
        signals_df: pd.DataFrame,
        module_allocation_df: pd.DataFrame,
        available_modules,
        logger_callback=None,
        is_status: str = 'NIS',
        redundancy: str = 'NonRed'
    ) -> None:
        """
        Allocate signals for a specific category (IS/Redundancy combination).
        
        Flow:
        1. Filter signals_df for (is_status, redundancy)
        2. Group by signal Type (AI, DI, DO, AO)
        3. For each type, allocate to compatible module slots
        4. Fill all 16 channels per slot before moving

        Args:
            signals_df: Signals DataFrame to update with allocations
            module_allocation_df: Module allocation table (Node, Slot, Module, Redundancy, IS_NIS, Channel_Capacity)
            available_modules: DataFrame/list of available module specifications
            logger_callback: Optional logging callback
            is_status: Filter for IS or NIS
            redundancy: Filter for Red or NonRed
        """
        # Filter signals for this category (IS/Redundancy)
        category_signals = signals_df[
            (signals_df['IS'] == is_status) & 
            (signals_df['Redundancy'] == redundancy) &
            (signals_df['Node'].isna())  # Only unallocated signals
        ]
        
        if category_signals.empty:
            if logger_callback:
                logger_callback(f"No unallocated signals for {is_status}-{redundancy}")
            return
        
        if logger_callback:
            logger_callback(f"\nAllocating {len(category_signals)} signals for {is_status}-{redundancy}")
            # Show sample of signals being allocated
            if len(category_signals) > 0:
                signals_sample = category_signals[['PID_TAG', 'Type', 'IS', 'Redundancy']].drop_duplicates()
                logger_callback(f"  Sample signals ({len(signals_sample)} unique): {signals_sample.head(3).to_dict('records')}")
        
        # Group signals by type and allocate
        for signal_type in ['AI', 'DI', 'DO', 'AO']:
            type_signals = category_signals[category_signals['Type'] == signal_type]
            if type_signals.empty:
                continue
            
            # Get target module type for this signal type
            target_module_type = self._get_target_module_for_type(signal_type, available_modules)
            if not target_module_type:
                if logger_callback:
                    logger_callback(f"  No module type found for {signal_type}")
                continue
            
            if logger_callback:
                logger_callback(f"  {signal_type} → {target_module_type} ({len(type_signals)} signals)")
            
            # Filter module allocation for correct redundancy, IS/NIS, and module type
            redundancy_filter = 'Yes' if redundancy == 'Red' else 'No'
            compatible_slots = module_allocation_df[
                (module_allocation_df['Redundancy'] == redundancy_filter) &
                (module_allocation_df['IS_NIS'] == is_status) &
                (module_allocation_df['Module'].str.contains(target_module_type.split('-')[0], na=False, case=False))
            ]
            
            if compatible_slots.empty:
                # Enhanced diagnostic logging
                if logger_callback:
                    logger_callback(f"    WARNING: No compatible slots for {signal_type} ({target_module_type})")
                    logger_callback(f"      Searching for: Redundancy={redundancy_filter}, IS_NIS={is_status}, Module starts with '{target_module_type.split('-')[0]}'")
                    
                    # Show what's available in module_allocation_df
                    red_filter_result = module_allocation_df[module_allocation_df['Redundancy'] == redundancy_filter]
                    logger_callback(f"      Available slots with Redundancy={redundancy_filter}: {len(red_filter_result)}")
                    if not red_filter_result.empty:
                        logger_callback(f"        IS_NIS values present: {red_filter_result['IS_NIS'].unique().tolist()}")
                        logger_callback(f"        Module values present: {red_filter_result['Module'].unique().tolist()}")
                    
                    is_nis_filter_result = module_allocation_df[module_allocation_df['IS_NIS'] == is_status]
                    logger_callback(f"      Available slots with IS_NIS={is_status}: {len(is_nis_filter_result)}")
                    if not is_nis_filter_result.empty:
                        logger_callback(f"        Redundancy values: {is_nis_filter_result['Redundancy'].unique().tolist()}")
                        logger_callback(f"        Module values: {is_nis_filter_result['Module'].unique().tolist()}")
                    
                    logger_callback(f"      Total module_allocation_df rows: {len(module_allocation_df)}")
                    logger_callback(f"      All unique Redundancy values: {module_allocation_df['Redundancy'].unique().tolist()}")
                    logger_callback(f"      All unique IS_NIS values: {module_allocation_df['IS_NIS'].unique().tolist()}")
                continue
            
            # Allocate signals to slots
            self._fill_slots_for_type(
                signals_df, type_signals, compatible_slots, logger_callback
            )
    
    def _fill_slots_for_type(
        self,
        signals_df: pd.DataFrame,
        type_signals: pd.DataFrame,
        compatible_slots: pd.DataFrame,
        logger_callback=None
    ) -> None:
        """
        Fill slots with signals of a specific type, filling all 16 channels per slot.
        
        Args:
            signals_df: Main signals DataFrame to update
            type_signals: Filtered signals for this type (from the working copy)
            compatible_slots: Filtered slots that can accept this type
            logger_callback: Optional logging callback
        """
        slot_index = 0
        skipped_slots = set()
        
        for _, signal_row in type_signals.iterrows():
            pid = signal_row['PID_TAG']
            is_redundant = signal_row['Redundancy'] == 'Red'
            
            # Find next available slot
            while slot_index < len(compatible_slots):
                current_slot_row = compatible_slots.iloc[slot_index]
                node = int(current_slot_row['Node'])
                slot = int(current_slot_row['Slot'])
                module_name = current_slot_row['Module']
                
                slot_key = (node, slot)
                
                # Skip this slot if it was marked to be skipped
                if slot_key in skipped_slots:
                    slot_index += 1
                    continue
                
                # Get current channel usage for this slot
                if slot_key not in self.slot_channel_usage:
                    self.slot_channel_usage[slot_key] = 0
                
                current_channel = self.slot_channel_usage[slot_key] + 1
                
                # Check if slot has available channels
                if current_channel <= 16:
                    # Allocate signal to this slot and channel
                    sig_idx = signals_df[signals_df['PID_TAG'] == pid].index[0]
                    signals_df.at[sig_idx, 'Node'] = node
                    signals_df.at[sig_idx, 'Slot'] = slot
                    signals_df.at[sig_idx, 'Channel'] = current_channel
                    signals_df.at[sig_idx, 'Module'] = module_name
                    
                    self.slot_channel_usage[slot_key] = current_channel
                    self.processed_signals.add(pid)
                    
                    # If redundant signal, skip next slot as they must pair
                    if is_redundant and slot_index + 1 < len(compatible_slots):
                        next_slot_row = compatible_slots.iloc[slot_index + 1]
                        next_slot_key = (int(next_slot_row['Node']), int(next_slot_row['Slot']))
                        skipped_slots.add(next_slot_key)
                    
                    # Move to next signal
                    slot_index += 1
                    break
                else:
                    # This slot is full, move to next
                    slot_index += 1
            
            
            # If we couldn't find a slot, signal remains unallocated

    def _get_target_module_for_type(
        self,
        signal_type: str,
        available_modules
    ) -> str:
        """
        Determine which module type should handle this signal based on Type.

        Args:
            signal_type: Signal type (AI, AO, DI, DO, etc.)
            available_modules: DataFrame or list with module specifications

        Returns:
            Module name (e.g., SAI-143H) or None if not found
        """
        # Map signal types to IO types
        type_io_map = {
            'AI': 'AI',
            'AO': 'AO',
            'DI': 'DI',
            'DO': 'DO'
        }

        target_io_type = type_io_map.get(signal_type, None)
        if not target_io_type:
            return None

        # Handle both DataFrame and list/dict formats
        if isinstance(available_modules, pd.DataFrame):
            if available_modules.empty:
                return None
            # Find module for this IO_Type (should be first available)
            matching = available_modules[available_modules['IO_Type'] == target_io_type]
            if not matching.empty:
                return matching.iloc[0]['Module']
        else:
            # Handle list of dicts
            for module in (available_modules if isinstance(available_modules, list) else []):
                if module.get('IO_Type') == target_io_type:
                    return module.get('Module')
        
        return None
