"""Nest Loading & IO Assignment Service - Channel allocation and I/O assignment logic."""

from typing import Dict, List
import pandas as pd
from domain.services.channel_allocator import ChannelAllocator
from domain.services.module_calculator import ModuleCalculator


class NestLoadingService:
    """Service to handle Nest Loading & IO Assignment workflows."""

    @staticmethod
    def process_nest_loading(
        input_file: str,
        design_input_results: Dict,
        logger_callback=None
    ) -> Dict:
        """
        Main orchestration for Nest Loading & IO Assignment.
        
        Takes design input review results and allocates signals to specific
        module channels with Node, Slot, Channel assignments.
        
        Args:
            input_file: Path to input Excel file
            design_input_results: Results from DesignInputReviewService
            logger_callback: Optional callback function for logging
        
        Returns:
            Dictionary with all nest loading results including updated signal table
        """
        def log(msg):
            """Wrapper to ensure logging always happens."""
            if logger_callback:
                logger_callback(msg)
            # Protect against encoding errors on some consoles (e.g. Windows cp1252)
            try:
                print(f"[NEST_LOADING] {msg}")
            except UnicodeEncodeError:
                safe_msg = str(msg).encode('ascii', 'replace').decode('ascii')
                print(f"[NEST_LOADING] {safe_msg}")
        
        log("Starting Nest Loading & IO Assignment...")
        log(f"Logger callback: {'Provided' if logger_callback else 'NOT PROVIDED'}")

        try:
            # Prepare consolidated signals DataFrame
            log("Preparing consolidated signals...")
            consolidated_signals = NestLoadingService._prepare_consolidated_signals(
                design_input_results, log
            )
            # Normalize Redundancy column using domain logic
            from domain.services.channel_allocator import ChannelAllocator
            consolidated_signals = ChannelAllocator.normalize_redundancy_column(consolidated_signals)
            
            log(f"Consolidated signals shape: {consolidated_signals.shape if not consolidated_signals.empty else 'EMPTY'}")
            
            if consolidated_signals.empty:
                log("ERROR: Consolidated signals is empty!")
                return {
                    "status": "error",
                    "message": "No signals available for channel allocation"
                }

            # Filter out SOFT signals (they don't need hardware allocation)
            soft_signals = consolidated_signals[consolidated_signals['Type'] == 'SOFT']
            soft_count = len(soft_signals)
            if soft_count > 0:
                log(f"Filtering out {soft_count} SOFT signals (software only, no hardware allocation needed)")
                consolidated_signals = consolidated_signals[consolidated_signals['Type'] != 'SOFT']
                log(f"After filtering SOFT: {len(consolidated_signals)} signals remain for allocation")

            if consolidated_signals.empty:
                log("WARNING: No hardware signals to allocate (all were SOFT)")
                return {
                    "status": "success",
                    "signals_with_allocation": pd.DataFrame(),
                    "allocation_summary": {"total": soft_count, "allocated": 0, "unallocated": soft_count},
                    "unallocated_signals": pd.DataFrame()
                }

            # Log signal summary
            is_red_count = len(consolidated_signals[(consolidated_signals['IS'] == 'IS') & (consolidated_signals['Redundancy'] == 'Red')])
            is_nonred_count = len(consolidated_signals[(consolidated_signals['IS'] == 'IS') & (consolidated_signals['Redundancy'] == 'NonRed')])
            nis_red_count = len(consolidated_signals[(consolidated_signals['IS'] == 'NIS') & (consolidated_signals['Redundancy'] == 'Red')])
            nis_nonred_count = len(consolidated_signals[(consolidated_signals['IS'] == 'NIS') & (consolidated_signals['Redundancy'] == 'NonRed')])
            
            log(f"Processing {len(consolidated_signals)} signals...")
            log(f"Signal distribution:")
            log(f"  IS-Red: {is_red_count}")
            log(f"  IS-NonRed: {is_nonred_count}")
            log(f"  NIS-Red: {nis_red_count}")
            log(f"  NIS-NonRed: {nis_nonred_count}")
            
            # Log signal types distribution
            type_dist = consolidated_signals['Type'].value_counts().to_dict()
            log(f"Signal types: {dict(type_dist)}")
            
            # Get module allocation DataFrame (from design input review)
            module_allocation_df = design_input_results.get('slot_allocation_details_df', pd.DataFrame())
            # Normalize Redundancy column to 'Yes'/'No' for consistent matching
            from domain.services.channel_allocator import ChannelAllocator
            module_allocation_df = ChannelAllocator.normalize_redundancy_column(module_allocation_df)
            if module_allocation_df.empty:
                log("ERROR: Module allocation DataFrame not found in design input results")
                return {
                    "status": "error",
                    "message": "Module allocation data not available"
                }
            
            # Log module allocation summary
            available_modules_df = design_input_results.get('available_modules', pd.DataFrame())
            red_slots = len(module_allocation_df[module_allocation_df['Redundancy'] == 'Yes'])
            nonred_slots = len(module_allocation_df[module_allocation_df['Redundancy'] == 'No'])
            log(f"Module allocation structure: {len(module_allocation_df)} total slots ({red_slots} for Redundant, {nonred_slots} for Non-Redundant)")
            log(f"Available modules: {len(available_modules_df)} module types")
            
            # Log module distribution by type
            if not module_allocation_df.empty:
                module_dist = module_allocation_df['Module'].value_counts().to_dict()
                log(f"Module distribution: {dict(module_dist)}")

            # Analyze category compatibility using domain logic
            log("\nAnalyzing category compatibility...")
            category_compatibility_df = ModuleCalculator.analyze_category_compatibility(
                consolidated_signals, 
                module_allocation_df
            )
            
            # Display compatibility analysis from DataFrame
            log("\n" + "="*80)
            log("DEBUG: CATEGORY COMPATIBILITY ANALYSIS")
            log("="*80)
            
            if not category_compatibility_df.empty:
                # Group by category for better display
                categories = category_compatibility_df['Category'].unique()
                for category in categories:
                    cat_rows = category_compatibility_df[category_compatibility_df['Category'] == category]
                    
                    # Get first row for category-level stats
                    first_row = cat_rows.iloc[0]
                    total_slots = first_row['Total_Category_Slots']
                    total_signals = first_row['Category_Signal_Total']
                    
                    log(f"\n{category}:")
                    log(f"  Slots Available: {total_slots}")
                    log(f"  Signals in Category: {total_signals}")
                    
                    # Show signal type details
                    if len(cat_rows) > 0:
                        log(f"  Type → Module Matching:")
                        for _, row in cat_rows.iterrows():
                            sig_type = row['Signal_Type']
                            expected = row['Expected_Module']
                            available = row['Available']
                            slots = row['Available_Slots']
                            status = "✓" if available else "✗"
                            log(f"    {status} {sig_type} → {expected} ({slots} slots available)")
            else:
                log("No category compatibility data available")
            
            log("="*80 + "\n")

            # Allocate signals to channels (pass DataFrame directly, no pre-categorized lists)
            log("Starting channel allocation...")
            channel_allocator = ChannelAllocator()
            signals_with_allocation = channel_allocator.allocate_signals_to_channels(
                signals_df=consolidated_signals,
                module_allocation_df=module_allocation_df,
                available_modules=available_modules_df,
                logger_callback=log
            )

            log("Channel allocation complete.")

            # Convert Redundancy column to 'Yes'/'No' for output consistency
            if 'Redundancy' in signals_with_allocation.columns:
                signals_with_allocation['Redundancy'] = signals_with_allocation['Redundancy'].apply(
                    lambda x: 'Yes' if str(x).strip().lower() in ['yes', 'red', 'redundant'] else 'No'
                )

            # Clean up duplicate columns - remove old redundancy columns if they exist
            if 'IO Redundancy' in signals_with_allocation.columns:
                signals_with_allocation = signals_with_allocation.drop(columns=['IO Redundancy'])
            if 'IS/Non-IS' in signals_with_allocation.columns:
                signals_with_allocation = signals_with_allocation.drop(columns=['IS/Non-IS'])

            # Ensure placeholder rows (blank channels) appear in correct order
            if all(col in signals_with_allocation.columns for col in ['Node', 'Slot', 'Channel']):
                signals_with_allocation = signals_with_allocation.sort_values(
                    by=['Node', 'Slot', 'Channel'],
                    na_position='last'
                ).reset_index(drop=True)

            # Drop duplicate tag column (use PID_TAG as the canonical identifier)
            if 'Tag' in signals_with_allocation.columns:
                signals_with_allocation = signals_with_allocation.drop(columns=['Tag'])

            return {
                "status": "success",
                "signals_with_allocation": signals_with_allocation,
                "allocation_summary": NestLoadingService._create_allocation_summary(signals_with_allocation),
                "unallocated_signals": NestLoadingService._get_unallocated_signals(signals_with_allocation),
                "category_compatibility": category_compatibility_df
            }

        except Exception as e:
            log(f"ERROR during nest loading: {str(e)}")
            import traceback
            log(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e)
            }

    @staticmethod
    def _prepare_consolidated_signals(design_input_results: Dict, logger_callback=None) -> pd.DataFrame:
        """
        Prepare consolidated signals DataFrame from design input results.
        
        Converts signal_data list to DataFrame with IS and Redundancy columns.
        
        Args:
            design_input_results: Results from DesignInputReviewService
            logger_callback: Optional logging callback
        
        Returns:
            DataFrame with consolidated signal data
        """
        signal_data = design_input_results.get('signal_data', [])
        
        if not signal_data:
            if logger_callback:
                logger_callback("No signal data available")
            return pd.DataFrame()
        
        # Create DataFrame from signal data
        df = pd.DataFrame(signal_data)
        
        # Add IS and Redundancy columns if not present
        if 'IS' not in df.columns and 'IS/Non-IS' in df.columns:
            df['IS'] = df['IS/Non-IS'].apply(lambda x: 'IS' if str(x) == 'IS' else 'NIS')
        
        if 'Redundancy' not in df.columns and 'IO Redundancy' in df.columns:
            df['Redundancy'] = df['IO Redundancy'].apply(lambda x: 'Red' if str(x).lower() in ['yes', 'redundant', 'red'] else 'NonRed')
        
        return df

    @staticmethod
    @staticmethod
    def _build_usable_channels_map(available_modules: List[Dict]) -> Dict:
        """
        Build a map of usable channels per module type.
        
        Args:
            available_modules: List of module dictionaries with specifications
        
        Returns:
            Dict mapping module names to usable channel counts
        """
        usable_channels_map = {}

        if not available_modules:
            # No module data available: emit empty map and rely on upstream data sources.
            # Avoid hard-coded module names/sizes in domain logic.
            return {}

        for module in available_modules:
            if isinstance(module, dict):
                module_name = module.get('Module', '')
                usable_channels = module.get('Usable_Channels', 16)
                if module_name:
                    usable_channels_map[module_name] = usable_channels

        return usable_channels_map

    @staticmethod
    def _create_allocation_summary(signals_df: pd.DataFrame) -> Dict:
        """
        Create summary statistics for channel allocation.
        
        Args:
            signals_df: DataFrame with allocation results
        
        Returns:
            Summary statistics
        """
        # Treat placeholder rows (if present) as non-signals for summary purposes
        if 'Placeholder' in signals_df.columns:
            real_signals = signals_df[signals_df['Placeholder'] != True]
        else:
            real_signals = signals_df

        total_signals = len(real_signals)
        allocated = len(real_signals[real_signals['Node'].notna()])
        unallocated = total_signals - allocated

        # Count by node
        nodes_used = real_signals[real_signals['Node'].notna()]['Node'].unique()

        return {
            "total_signals": total_signals,
            "allocated_signals": allocated,
            "unallocated_signals": unallocated,
            "nodes_used": int(max(nodes_used)) if len(nodes_used) > 0 else 0,
            "allocation_percentage": (allocated / total_signals * 100) if total_signals > 0 else 0
        }

    @staticmethod
    def _get_unallocated_signals(signals_df: pd.DataFrame) -> List[str]:
        """
        Get list of signals that failed to allocate.
        
        Args:
            signals_df: DataFrame with allocation results
        
        Returns:
            List of unallocated PID_TAGs
        """
        if 'Placeholder' in signals_df.columns:
            signals_df = signals_df[signals_df['Placeholder'] != True]
        unallocated = signals_df[signals_df['Node'].isna()]
        return unallocated['PID_TAG'].tolist() if not unallocated.empty else []

    @staticmethod
    def validate_constraints(channel_allocation: Dict) -> Dict:
        """
        Validate that channel allocation respects hardware constraints.
        
        Args:
            channel_allocation: Channel allocation from allocate_channels()
        
        Returns:
            Validation result with any constraint violations
        """
        # TODO: Implement constraint validation
        return {
            "valid": True,
            "message": "Constraint validation logic to be implemented"
        }

    @staticmethod
    def generate_nest_loading_report(channel_allocation: Dict) -> Dict:
        """
        Generate nest loading report with channel assignments.
        
        Args:
            channel_allocation: Validated channel allocation
        
        Returns:
            Report data ready for export
        """
        # TODO: Implement report generation
        return {
            "report": "placeholder",
            "message": "Report generation logic to be implemented"
        }


