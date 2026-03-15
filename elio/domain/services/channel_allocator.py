"""Channel Allocator - Maps signals to specific module slots and channels."""

import pandas as pd
from typing import Dict, List, Tuple




class ChannelAllocator:
    """Allocates I/O signals to hardware module channels with redundancy handling."""

    @staticmethod
    def normalize_redundancy_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize Redundancy column to 'Yes'/'No' for consistency with frontend and assignment.
        Args:
            df: DataFrame with Redundancy column ('Red'/'NonRed', etc.)
        Returns:
            DataFrame with normalized Redundancy column
        """
        if 'Redundancy' in df.columns:
            df['Redundancy'] = df['Redundancy'].astype(str).str.strip().str.lower()
            df['Redundancy'] = df['Redundancy'].apply(lambda x: 'Yes' if x in ['red', 'yes', 'redundant'] else 'No')
        return df

    @staticmethod
    def normalize_is_non_is_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize IS/Non-IS columns to 'IS'/'NIS' and add a unified 'IS' column for assignment.

        Supports various column names used in different upstream sources:
        - 'IS_Non_IS'
        - 'IS_NIS'
        - 'IS/Non-IS'
        """
        # Normalize all values to strings and handle missing values safely.
        def _normalize_series(series):
            return series.fillna('').astype(str).str.strip().str.upper()

        if 'IS_NIS' in df.columns:
            df['IS_NIS'] = _normalize_series(df['IS_NIS'])
            df['IS_NIS'] = df['IS_NIS'].apply(lambda x: 'IS' if x.startswith('IS') else 'NIS')
            df['IS'] = df['IS_NIS']
            df['IS_Non_IS'] = df['IS_NIS']
        elif 'IS_Non_IS' in df.columns:
            df['IS_Non_IS'] = _normalize_series(df['IS_Non_IS'])
            df['IS_Non_IS'] = df['IS_Non_IS'].apply(lambda x: 'IS' if x.startswith('IS') else 'NIS')
            df['IS'] = df['IS_Non_IS']
        elif 'IS/Non-IS' in df.columns:
            df['IS/Non-IS'] = _normalize_series(df['IS/Non-IS'])
            df['IS_Non_IS'] = df['IS/Non-IS'].apply(lambda x: 'IS' if x.startswith('IS') else 'NIS')
            df['IS'] = df['IS_Non_IS']
        else:
            df['IS_Non_IS'] = 'NIS'
            df['IS'] = 'NIS'
        return df

    @staticmethod
    def get_canonical_type(value: str) -> str:
        """Normalize a value to a canonical signal type (AI/DI/DO/AO/SOFT).

        This is used to translate values like "DI-R", "AI", or other variant strings
        into a consistent base type for matching.
        """
        if value is None:
            return ''
        v = str(value).upper().strip()
        for base in ['AI', 'DI', 'DO', 'AO', 'SOFT']:
            if base in v:
                return base
        return v

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
        Assign signals directly from the processed DataFrame, using normalized signal types and redundancy values.
        No category segregation; match signals to slots based on Type and Redundancy.
        """
        if logger_callback:
            logger_callback("Initializing channel allocation with module allocation DataFrame...")

        # Create working copy and normalize signal types
        result_df = signals_df.copy()
        result_df['Node'] = None
        result_df['Slot'] = None
        result_df['Channel'] = None
        result_df['Module'] = None

        # Normalize IS_Non_IS column and propagate 'IS' column
        result_df = ChannelAllocator.normalize_is_non_is_column(result_df)

        # Normalize signal types (AI-R, DI-R, etc. → AI, DI, etc.)
        result_df['Type'] = result_df['Type'].apply(ChannelAllocator.get_canonical_type)

        # Normalize Redundancy values in both DataFrames (Yes/No)
        def normalize_redundancy(val):
            v = str(val).strip().lower()
            return 'Yes' if v in ['yes', 'red', 'redundant'] else 'No'
        result_df = ChannelAllocator.normalize_redundancy_column(result_df)
        module_allocation_df = ChannelAllocator.normalize_redundancy_column(module_allocation_df)

        # Normalize IS/Non-IS columns in slot allocation DataFrame
        # (Supports IS_NIS, IS_Non_IS, IS/Non-IS as input column names)
        if any(c in module_allocation_df.columns for c in ['IS_NIS', 'IS_Non_IS', 'IS/Non-IS']):
            module_allocation_df = ChannelAllocator.normalize_is_non_is_column(module_allocation_df)

        # Assign signals directly
        # Sort slots to ensure deterministic ordering for redundancy slot reservation.
        module_allocation_df = module_allocation_df.sort_values(by=['Node', 'Slot'])

        slot_usage = {}
        slot_order = []
        for idx, slot_row in module_allocation_df.iterrows():
            node = int(slot_row['Node'])
            slot = int(slot_row['Slot'])
            module_name = slot_row['Module']
            slot_key = (node, slot)

            # Determine slot type using IO_Type column (must be provided in slot allocation details).
            # If missing, we treat it as unknown and rely on the source data being correct.
            slot_type = slot_row.get('IO_Type', None)
            if slot_type:
                slot_type = ChannelAllocator.get_canonical_type(slot_type)
            else:
                slot_type = ''  # No inferencing; assume input table provides IO_Type

            # Use per-slot channel capacity (from slot allocation DataFrame) if available
            slot_capacity = int(slot_row.get('Channel_Capacity', 16)) if slot_row.get('Channel_Capacity') is not None else 16

            slot_usage[slot_key] = {
                'module_name': module_name,
                'Type': slot_type,
                'Redundancy': normalize_redundancy(slot_row.get('Redundancy', 'No')),
                'IS': slot_row.get('IS', slot_row.get('IS_Non_IS', 'NIS')),
                'capacity': slot_capacity,
                # next_channel is the next free channel for this slot (1..capacity)
                'next_channel': self.slot_channel_usage.get(slot_key, 1),
                'reserved': False,
                'reserved_slot_created': False,
            }
            slot_order.append(slot_key)

        # Assign signals
        unassigned_log_count = 0
        max_unassigned_logs = 5

        for idx, signal_row in result_df.iterrows():
            pid = signal_row['PID_TAG']
            signal_type = signal_row['Type']
            signal_red = signal_row['Redundancy']
            signal_is = signal_row['IS']

            # Skip already assigned signals (e.g. placeholders or previously assigned)
            if pd.notna(signal_row.get('Node')) and pd.notna(signal_row.get('Slot')):
                continue

            assigned = False
            failed_conditions = []

            # Find slots that match type, redundancy, IS and are not reserved
            matching_slots = [
                k for k in slot_order
                if slot_usage[k]['Type'] == signal_type and not slot_usage[k].get('reserved', False)
            ]
            if not matching_slots:
                available_types = sorted({v['Type'] for v in slot_usage.values()})
                failed_conditions.append(f"No slots for Type={signal_type} (available types: {available_types})")
            else:
                for slot_key in matching_slots:
                    slot_info = slot_usage[slot_key]

                    if slot_info['Redundancy'] != signal_red:
                        failed_conditions.append(f"Redundancy mismatch: slot={slot_info['Redundancy']} signal={signal_red}")
                        continue
                    if slot_info['IS'] != signal_is:
                        failed_conditions.append(f"IS mismatch: slot={slot_info['IS']} signal={signal_is}")
                        continue

                    channel_num = slot_info['next_channel']
                    capacity = slot_info['capacity']

                    if signal_red == 'Yes':
                        # Full slot reserved for redundant signals; we only ever assign to this slot's channels.
                        if channel_num > capacity:
                            failed_conditions.append(f"Slot {slot_key} full (capacity {capacity})")
                            continue

                        # Assign redundant signal to this slot & channel
                        result_df.at[idx, 'Node'] = slot_key[0]
                        result_df.at[idx, 'Slot'] = slot_key[1]
                        result_df.at[idx, 'Channel'] = channel_num
                        result_df.at[idx, 'Module'] = slot_info['module_name']
                        self.processed_signals.add(pid)

                        # If this slot has not yet reserved the next slot, reserve it now.
                        if not slot_info.get('reserved_slot_created', False):
                            slot_info['reserved_slot_created'] = True
                            next_slot = None
                            current_index = slot_order.index(slot_key)
                            for next_key in slot_order[current_index + 1:]:
                                next_info = slot_usage[next_key]
                                if (
                                    next_info['Type'] == signal_type
                                    and next_info['Redundancy'] == signal_red
                                    and next_info['IS'] == signal_is
                                    and not next_info.get('reserved', False)
                                ):
                                    next_slot = next_key
                                    break

                            if next_slot:
                                slot_usage[next_slot]['reserved'] = True
                                placeholder = {c: None for c in result_df.columns}
                                placeholder['Node'] = next_slot[0]
                                placeholder['Slot'] = next_slot[1]
                                placeholder['Channel'] = None
                                placeholder['Module'] = slot_info['module_name']
                                placeholder['Type'] = signal_type
                                placeholder['Redundancy'] = signal_red
                                placeholder['IS'] = signal_is
                                placeholder['Placeholder'] = True
                                result_df = pd.concat([result_df, pd.DataFrame([placeholder])], ignore_index=True)

                        # Advance to next channel in current slot.
                        slot_info['next_channel'] = channel_num + 1
                        self.slot_channel_usage[slot_key] = max(0, slot_info['next_channel'] - 1)
                        assigned = True
                        break

                    # Non-redundant signal assignment
                    if channel_num > capacity:
                        failed_conditions.append(f"Slot {slot_key} full (capacity {capacity})")
                        continue

                    result_df.at[idx, 'Node'] = slot_key[0]
                    result_df.at[idx, 'Slot'] = slot_key[1]
                    result_df.at[idx, 'Channel'] = channel_num
                    result_df.at[idx, 'Module'] = slot_info['module_name']
                    self.processed_signals.add(pid)

                    slot_info['next_channel'] = channel_num + 1
                    self.slot_channel_usage[slot_key] = max(0, slot_info['next_channel'] - 1)
                    assigned = True
                    break

            if not assigned:
                # Limit log spam when many signals cannot be assigned.
                # Only show details for the first few unassigned signals.
                unassigned_log_count += 1
                if logger_callback and unassigned_log_count <= max_unassigned_logs:
                    display_conditions = failed_conditions[:5]
                    if len(failed_conditions) > 5:
                        display_conditions.append(f"...(+{len(failed_conditions) - 5} more)")

                    logger_callback(f"[DEBUG] Could not assign signal {pid} (Type={signal_type}, Redundancy={signal_red}, IS={signal_is})")
                    logger_callback(f"[DEBUG] Assignment failed due to: {display_conditions if display_conditions else 'No available slot/channel'}")
                elif logger_callback and unassigned_log_count == max_unassigned_logs + 1:
                    logger_callback(f"[DEBUG] ...skipping further unassigned signal details (limit {max_unassigned_logs})")

            if not assigned:
                # Limit log spam when many signals cannot be assigned.
                # Only show details for the first few unassigned signals.
                unassigned_log_count += 1
                if logger_callback and unassigned_log_count <= max_unassigned_logs:
                    display_conditions = failed_conditions[:5]
                    if len(failed_conditions) > 5:
                        display_conditions.append(f"...(+{len(failed_conditions) - 5} more)")

                    logger_callback(f"[DEBUG] Could not assign signal {pid} (Type={signal_type}, Redundancy={signal_red}, IS={signal_is})")
                    logger_callback(f"[DEBUG] Assignment failed due to: {display_conditions if display_conditions else 'No available slot/channel'}")
                elif logger_callback and unassigned_log_count == max_unassigned_logs + 1:
                    logger_callback(f"[DEBUG] ...skipping further unassigned signal details (limit {max_unassigned_logs})")

        # Debug: Show 5 sample unallocated rows for each signal type
        if logger_callback:
            for t in ['AI', 'DI', 'DO', 'AO']:
                unallocated = result_df[(result_df['Type'] == t) & (result_df['Node'].isna())]
                if not unallocated.empty:
                    logger_callback(f"[DEBUG] Unallocated {t} signals: {len(unallocated)}")
                    logger_callback(unallocated[['PID_TAG', 'Type', 'Redundancy', 'IS', 'Node', 'Slot', 'Channel']].head(5).to_dict('records'))

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

        # Debug: Show 5 sample rows for this category with None for Node, Slot, Channel
        if logger_callback:
            logger_callback(f"\n[DEBUG] {is_status}-{redundancy} unallocated signals: {len(category_signals)}")
            if not category_signals.empty:
                debug_cols = ['PID_TAG', 'Type', 'IS', 'Redundancy', 'Node', 'Slot', 'Channel']
                logger_callback(f"  [DEBUG] Sample rows (None for Node/Slot/Channel):")
                logger_callback(category_signals[debug_cols].head(5).to_dict('records'))

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
        skipped_slots = set()
        slot_channel_capacity = 16  # Default channel capacity per slot

        # Prepare a list of available slots and their current channel usage
        slot_usage = {}
        for idx, slot_row in compatible_slots.iterrows():
            node = int(slot_row['Node'])
            slot = int(slot_row['Slot'])
            module_name = slot_row['Module']
            slot_key = (node, slot)
            slot_usage[slot_key] = {
                'module_name': module_name,
                'used_channels': self.slot_channel_usage.get(slot_key, 0)
            }

        # Assign signals to slots, filling channels sequentially
        signal_idx = 0
        total_signals = len(type_signals)
        slot_keys = [k for k in slot_usage.keys() if k not in skipped_slots]
        slot_ptr = 0

        while signal_idx < total_signals and slot_ptr < len(slot_keys):
            slot_key = slot_keys[slot_ptr]
            module_name = slot_usage[slot_key]['module_name']
            used_channels = slot_usage[slot_key]['used_channels']

            # Prepare the next signal
            signal_row = type_signals.iloc[signal_idx]
            pid = signal_row['PID_TAG']
            is_redundant = str(signal_row.get('Redundancy', '')).strip().lower() == 'yes'

            # Reserve one slot per redundant signal (and leave the next slot blank)
            if is_redundant:
                # Assign this signal only to the current slot (channel 1)
                sig_idx = signals_df[signals_df['PID_TAG'] == pid].index[0]
                signals_df.at[sig_idx, 'Node'] = slot_key[0]
                signals_df.at[sig_idx, 'Slot'] = slot_key[1]
                signals_df.at[sig_idx, 'Channel'] = 1
                signals_df.at[sig_idx, 'Module'] = module_name

                # Mark this slot as used (no other signal should share it)
                slot_usage[slot_key]['used_channels'] = slot_channel_capacity
                self.slot_channel_usage[slot_key] = slot_channel_capacity
                self.processed_signals.add(pid)

                # Reserve the next slot (leave it blank in output)
                if slot_ptr + 1 < len(slot_keys):
                    reserved_slot_key = slot_keys[slot_ptr + 1]
                    skipped_slots.add(reserved_slot_key)

                    placeholder = {c: None for c in signals_df.columns}
                    placeholder['Node'] = reserved_slot_key[0]
                    placeholder['Slot'] = reserved_slot_key[1]
                    placeholder['Channel'] = None
                    placeholder['Module'] = module_name
                    placeholder['Type'] = signal_row.get('Type')
                    placeholder['Redundancy'] = 'Yes'
                    placeholder['IS'] = signal_row.get('IS')
                    placeholder['Placeholder'] = True
                    signals_df.loc[len(signals_df)] = placeholder

                    slot_keys = [k for k in slot_usage.keys() if k not in skipped_slots]
                    slot_ptr = slot_keys.index(slot_key)

                signal_idx += 1
                slot_ptr += 1
                continue

            # Non-redundant signals: fill slots by channel capacity
            while used_channels < slot_channel_capacity and signal_idx < total_signals:
                signal_row = type_signals.iloc[signal_idx]
                pid = signal_row['PID_TAG']

                sig_idx = signals_df[signals_df['PID_TAG'] == pid].index[0]
                signals_df.at[sig_idx, 'Node'] = slot_key[0]
                signals_df.at[sig_idx, 'Slot'] = slot_key[1]
                signals_df.at[sig_idx, 'Channel'] = used_channels + 1
                signals_df.at[sig_idx, 'Module'] = module_name

                self.slot_channel_usage[slot_key] = used_channels + 1
                slot_usage[slot_key]['used_channels'] = used_channels + 1
                self.processed_signals.add(pid)

                used_channels += 1
                signal_idx += 1

            # Move to next slot
            slot_ptr += 1

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
            Module name or None if not found
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
