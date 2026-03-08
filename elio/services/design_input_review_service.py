"""Design Input Review Service - Handles all signal processing and module allocation logic."""

import pandas as pd
from pathlib import Path
from typing import Dict, List
from infrastructure.excel_reader import ExcelReader
from domain.services.signal_classifier import SignalClassifier
from domain.services.module_calculator import ModuleCalculator
from domain.services.module_selector import ModuleSelector
from domain.services.rack_allocator import RackAllocator


class DesignInputReviewService:
    """Service to handle Design Input Review workflows."""

    @staticmethod
    def process_design_input(uploaded_file, user_config, col_mapping, logger_callback):
        """
        Process design input file and return all analysis results.
        
        Args:
            uploaded_file: Uploaded Excel file
            user_config: Configuration dictionary
            col_mapping: Column mapping from ExcelReader
            logger_callback: Function to log messages (called with message and level)
        
        Returns:
            Dictionary with all results or error
        """
        try:
            logger_callback("Reading Excel file...")
            signals = ExcelReader.read(uploaded_file)
            logger_callback(f"Successfully read {len(signals)} signals")
            
            # ====================================================================
            # SIGNAL SUMMARY ANALYSIS
            # ====================================================================
            results = {
                "signals": signals,
                "col_mapping": col_mapping,
                "summary_breakdown": {},
                "summary_table": {},
                "signal_data": [],
                "signal_spares_table": {},
                "available_modules": pd.DataFrame(),
                "module_allocation": pd.DataFrame(),
                "module_allocation_with_redundancy": pd.DataFrame(),
                "module_summary": pd.DataFrame(),
                "rack_allocation": {}
            }
            
            # Calculate signal distribution
            summary_breakdown = {}
            unclassified_count = 0
            
            for signal in signals:
                signal_type = signal.signal_type if signal.signal_type else "Unclassified"
                
                if signal.signal_type is None:
                    unclassified_count += 1
                    continue
                
                # Determine IS/Non-IS status
                is_status = "IS"
                if col_mapping.get("is_non_is") and signal.is_non_is:
                    is_status = signal.is_non_is if signal.is_non_is.upper().startswith("IS") else "Non-IS"
                else:
                    is_status = "IS" if signal.signal_type in user_config.get("is_types", []) else "Non-IS"
                
                # Determine Redundancy status
                redundancy_status = "Non-Redundant"
                if col_mapping.get("io_redundancy") and signal.io_redundancy:
                    redundancy_status = signal.io_redundancy
                else:
                    redundancy_status = "Redundant" if signal.signal_type in user_config.get("redundancy_types", []) else "Non-Redundant"
                
                # Create composite key
                key = f"{signal_type}|{is_status}|{redundancy_status}"
                summary_breakdown[key] = summary_breakdown.get(key, 0) + 1
            
            results["summary_breakdown"] = summary_breakdown
            
            # Build summary table
            summary_table = {}
            for signal_type in ["AI", "DI", "DO", "AO", "SOFT"]:
                is_count = 0
                non_is_count = 0
                redundant_count = 0
                non_redundant_count = 0
                
                for key, count in summary_breakdown.items():
                    parts = key.split("|")
                    if parts[0] == signal_type:
                        if parts[1] == "IS":
                            is_count += count
                        else:
                            non_is_count += count
                        
                        if parts[2] == "Redundant":
                            redundant_count += count
                        else:
                            non_redundant_count += count
                
                total_for_type = is_count + non_is_count
                if total_for_type > 0:
                    summary_table[signal_type] = {
                        "IS": is_count,
                        "Non-IS": non_is_count,
                        "Redundant": redundant_count,
                        "Non-Redundant": non_redundant_count,
                        "Total": total_for_type
                    }
            
            if unclassified_count > 0:
                summary_table["⚠ Unclassified"] = {
                    "IS": "-",
                    "Non-IS": "-",
                    "Redundant": "-",
                    "Non-Redundant": "-",
                    "Total": unclassified_count
                }
                logger_callback(f"WARNING: {unclassified_count} signals have unknown/unclassified type", "WARNING")
            
            results["summary_table"] = summary_table
            logger_callback(f"Summary: {len(summary_table)} signal types, {len(signals)} total signals")
            
            # ====================================================================
            # DETAILED SIGNAL DATA
            # ====================================================================
            signal_data = []
            for signal in signals:
                row = {
                    "Tag": signal.tag or "-",
                    "Type": signal.signal_type if signal.signal_type else "⚠ Unclassified",
                    "PID_TAG": signal.pid_tag or "-",
                }
                
                if col_mapping.get("signal_origin") and signal.signal_origin:
                    row["Signal Origin"] = signal.signal_origin
                else:
                    row["Signal Origin"] = user_config.get("system_type", "-")
                
                if col_mapping.get("io_redundancy") and signal.io_redundancy:
                    row["IO Redundancy"] = signal.io_redundancy
                else:
                    redundancy_mark = signal.signal_type in user_config.get("redundancy_types", []) if signal.signal_type else False
                    row["IO Redundancy"] = "Yes" if redundancy_mark else "No"
                
                if col_mapping.get("is_non_is") and signal.is_non_is:
                    row["IS/Non-IS"] = signal.is_non_is
                else:
                    is_mark = signal.signal_type in user_config.get("is_types", []) if signal.signal_type else False
                    row["IS/Non-IS"] = "IS" if is_mark else "Non-IS"
                
                row["JB Cable Name"] = signal.jb_cable_name or "-"
                signal_data.append(row)
            
            results["signal_data"] = signal_data
            logger_callback(f"Displayed {len(signal_data)} signals in data table")
            
            # ====================================================================
            # SIGNAL COUNTS WITH WIRED SPARES
            # ====================================================================
            wired_spares_percent = user_config.get("wired_spares", 0)
            
            if wired_spares_percent > 0 and summary_breakdown:
                signal_spares_table = SignalClassifier.build_signal_counts_table_with_spares(
                    summary_breakdown=summary_breakdown,
                    spare_percentage=wired_spares_percent
                )
                results["signal_spares_table"] = signal_spares_table
                
                logger_callback("\nDEBUG: Signal Distribution by Category (with spares):")
                for signal_type, table_row in signal_spares_table.items():
                    logger_callback(f"  {signal_type}: IS-Red({table_row['IS-Red']}+S{table_row['IS-Red Spares']}) | IS-NonRed({table_row['IS-NonRed']}+S{table_row['IS-NonRed Spares']}) | NIS-Red({table_row['NIS-Red']}+S{table_row['NIS-Red Spares']}) | NIS-NonRed({table_row['NIS-NonRed']}+S{table_row['NIS-NonRed Spares']}) = {table_row['Total']} total")
                
                for signal_type, table_row in signal_spares_table.items():
                    logger_callback(f"{signal_type}: IS-Red({table_row['IS-Red']})+Spares({table_row['IS-Red Spares']}) | IS-NonRed({table_row['IS-NonRed']})+Spares({table_row['IS-NonRed Spares']}) | NIS-Red({table_row['NIS-Red']})+Spares({table_row['NIS-Red Spares']}) | NIS-NonRed({table_row['NIS-NonRed']})+Spares({table_row['NIS-NonRed Spares']}) = {table_row['Total']} total")
                
                grand_total = sum([row["Total"] for row in signal_spares_table.values()])
                total_spares_added = sum([row["IS-Red Spares"] + row["IS-NonRed Spares"] + row["NIS-Red Spares"] + row["NIS-NonRed Spares"] for row in signal_spares_table.values()])
                logger_callback(f"Total Signals with Spares: {grand_total} signals (Spares added: {total_spares_added} @ {wired_spares_percent}%)")
            
            # ====================================================================
            # MODULE ALLOCATION
            # ====================================================================
            selected_io_types = user_config.get("io_types", [])
            temperature_rating = user_config.get("temperature_rating")
            
            if selected_io_types and wired_spares_percent > 0 and results["signal_spares_table"]:
                # Get available modules
                base_path = Path(__file__).parent.parent.parent
                excel_path = base_path / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
                
                if excel_path.exists():
                    available_modules = ModuleSelector.get_available_modules(
                        excel_path=str(excel_path),
                        selected_io_types=selected_io_types,
                        temperature_rating=temperature_rating
                    )
                    
                    # Filter to only IOM type modules (for dynamic channel allocation)
                    # Read Mounting_Rule to get which IO_Types have Type='IOM'
                    try:
                        mounting_rules_df = pd.read_excel(str(excel_path), sheet_name="Mounting_Rule")
                        iom_io_types = set(
                            mounting_rules_df[mounting_rules_df['Type'].astype(str).str.upper() == 'IOM']['IO_Type'].dropna().unique()
                        )
                        
                        # Filter available_modules DataFrame to only IOM types
                        if iom_io_types:
                            available_modules = available_modules[available_modules['IO_Type'].isin(iom_io_types)].reset_index(drop=True)
                            logger_callback(f"Filtered modules: {len(available_modules)} IOM modules available for allocation")
                        else:
                            logger_callback("Warning: No IOM type modules found in Mounting_Rule sheet")
                    except Exception as e:
                        logger_callback(f"Warning: Could not filter to IOM modules: {str(e)}")
                    
                    results["available_modules"] = available_modules
                    logger_callback(f"Available modules loaded: {len(available_modules)} modules found")
                    
                    # Calculate module allocation
                    module_allocation_df = ModuleCalculator.calculate_module_allocation(
                        signal_spares_table=results["signal_spares_table"],
                        available_modules=available_modules
                    )
                    results["module_allocation"] = module_allocation_df
                    
                    # Apply redundancy doubling
                    module_allocation_with_redundancy_df = ModuleCalculator.apply_redundancy_doubling(
                        allocation_df=module_allocation_df
                    )
                    results["module_allocation_with_redundancy"] = module_allocation_with_redundancy_df
                    
                    for _, row in module_allocation_with_redundancy_df.iterrows():
                        is_red = row.get("IS-Red_Modules", 0)
                        is_nonred = row.get("IS-NonRed_Modules", 0)
                        nis_red = row.get("NIS-Red_Modules", 0)
                        nis_nonred = row.get("NIS-NonRed_Modules", 0)
                        total = row.get("Total_Modules", 0)
                        io_type = row.get("IO_Type", "")
                        module = row.get("Module", "")
                        logger_callback(f"{io_type} (with redundancy): IS-Red({is_red}) + IS-NonRed({is_nonred}) + NIS-Red({nis_red}) + NIS-NonRed({nis_nonred}) = {total} total modules ({module})")
                    
                    # Calculate module summary
                    module_summary_df = ModuleCalculator.calculate_module_summary(
                        before_df=module_allocation_df,
                        after_df=module_allocation_with_redundancy_df
                    )
                    results["module_summary"] = module_summary_df
                    
                    for _, row in module_summary_df.iterrows():
                        single_mods = row.get("Single_Modules", 0)
                        dual_red_mods = row.get("Dual_Red_Modules", 0)
                        total_fio = row.get("Total_FIO_Modules", 0)
                        io_type = row.get("IO_Type", "")
                        logger_callback(f"{io_type} summary: Single({single_mods}) + Dual_Red({dual_red_mods}) = Total({total_fio}) modules")
                    
                    # Debug: Log detailed allocation before consolidation
                    logger_callback("\nDEBUG: Pre-Consolidation Allocation (by category):")
                    total_is_red = 0
                    total_is_nonred = 0
                    total_nis_red = 0
                    total_nis_nonred = 0
                    
                    for _, row in module_allocation_with_redundancy_df.iterrows():
                        is_red = row.get("IS-Red_Modules", 0)
                        is_nonred = row.get("IS-NonRed_Modules", 0)
                        nis_red = row.get("NIS-Red_Modules", 0)
                        nis_nonred = row.get("NIS-NonRed_Modules", 0)
                        io_type = row.get("IO_Type", "")
                        logger_callback(f"  {io_type}: IS-Red({is_red}) + IS-NonRed({is_nonred}) + NIS-Red({nis_red}) + NIS-NonRed({nis_nonred})")
                        total_is_red += is_red
                        total_is_nonred += is_nonred
                        total_nis_red += nis_red
                        total_nis_nonred += nis_nonred
                    
                    logger_callback(f"  TOTAL: IS-Red({total_is_red}) + IS-NonRed({total_is_nonred}) + NIS-Red({total_nis_red}) + NIS-NonRed({total_nis_nonred})")
                    if total_is_nonred == 0 and total_nis_nonred == 0:
                        logger_callback("  ⚠️ WARNING: No NonRed signals found! All signals are redundant. Check if this is expected based on your input config.")
                    
                    # Log allocation category map
                    allocation_map = ModuleCalculator.build_allocation_category_map(module_allocation_with_redundancy_df)
                    logger_callback("\nDEBUG: Module Category Distribution:")
                    for module_name, categories in allocation_map.items():
                        from collections import Counter
                        counts = Counter(categories)
                        logger_callback(f"  {module_name}: {dict(counts)}")
                        # Detailed breakdown
                        logger_callback(f"    Full list: {categories}")
                    
                    # Allocate modules to rack
                    rack_allocation = RackAllocator.allocate_modules_to_rack(
                        excel_path=str(excel_path),
                        module_summary=module_summary_df,
                        available_modules=available_modules
                    )
                    results["rack_allocation"] = rack_allocation
                    
                    if rack_allocation and "Error" not in rack_allocation:
                        total_allocated = sum(1 for node in rack_allocation.values() for slot in node.values() if slot and slot != "")
                        logger_callback(f"Module allocation complete: {total_allocated} slots filled across {len(rack_allocation)} nodes")
                        
                        # Get IOM slots from Mounting_Rule (constraints)
                        base_path = Path(__file__).parent.parent.parent
                        constraints_file = base_path / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
                        iom_slots_df = pd.DataFrame()
                        
                        if constraints_file.exists():
                            try:
                                iom_slots_df = ModuleCalculator.get_iom_slots_dataframe(str(constraints_file))
                                logger_callback(f"IOM slots read: {len(iom_slots_df)} slots found")
                            except Exception as e:
                                logger_callback(f"WARNING: Could not read IOM slots: {str(e)}")
                        
                        # Create unified Module Allocation DataFrame
                        # Single source of truth with: Node, Slot, Module, IS_NIS, Redundancy, Channel_Capacity
                        module_allocation_df = ModuleCalculator.create_module_allocation_dataframe(
                            rack_allocation=rack_allocation,
                            module_allocation_with_redundancy=module_allocation_with_redundancy_df,
                            available_modules=available_modules,
                            iom_slots_df=iom_slots_df
                        )
                        
                        results["slot_allocation_details_df"] = module_allocation_df
                        
                        if not module_allocation_df.empty:
                            # Analyze for summary statistics
                            slot_analysis_df = ModuleCalculator.analyze_slot_allocation(module_allocation_df)
                            results["slot_allocation_analysis"] = slot_analysis_df
                            
                            # Get values from single-row DataFrame
                            analysis = slot_analysis_df.iloc[0]
                            logger_callback(f"Allocated: {analysis['total_slots']} slots")
                            logger_callback(f"  IS: {analysis['is_count']} | NIS: {analysis['nis_count']}")
                            logger_callback(f"  Redundancy=Yes: {analysis['redundancy_yes_count']} | Redundancy=No: {analysis['redundancy_no_count']}")
                            logger_callback(f"  Total Capacity: {analysis['total_channel_capacity']} channels")
                            
                            # Display module allocation structure for debugging
                            logger_callback("\n" + "="*80)
                            logger_callback("DEBUG: MODULE ALLOCATION COMPLETE")
                            logger_callback("="*80 + "\n")
            
            results["success"] = True
            return results
        
        except Exception as e:
            error_msg = f"Error processing design input: {str(e)}"
            logger_callback(error_msg, "ERROR")
            return {"success": False, "error": error_msg}


