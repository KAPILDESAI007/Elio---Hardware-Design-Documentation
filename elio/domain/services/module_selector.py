import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path


class ModuleSelector:

    @staticmethod
    def select(signal_type, templates):
        for t in templates:
            if t.signal_type == signal_type:
                return t
        raise Exception(f"No template for {signal_type}")

    @staticmethod
    def load_module_catalog_from_excel(excel_path: str) -> pd.DataFrame:
        """
        Load the IO_Module_Catalog sheet from Yokogawa constraints Excel file.
        
        Args:
            excel_path: Path to the Yokogawa_SIS_Constraints_Model_v3.xlsx file
            
        Returns:
            DataFrame containing the module catalog
        """
        try:
            df_catalog = pd.read_excel(excel_path, sheet_name="IO_Module_Catalog")
            return df_catalog
        except Exception as e:
            raise Exception(f"Error reading module catalog: {str(e)}")

    @staticmethod
    def filter_modules_by_io_family(df_catalog: pd.DataFrame, selected_io_types: List[str]) -> pd.DataFrame:
        """
        Filter modules by IO Family type (FIO, NIO, etc.).
        
        Args:
            df_catalog: Module catalog DataFrame
            selected_io_types: List of selected IO types (e.g., ["FIO", "NIO"])
            
        Returns:
            Filtered DataFrame with matching Family
        """
        if not selected_io_types or len(selected_io_types) == 0:
            return df_catalog
        
        # Filter by Family column matching selected IO types
        if "Family" in df_catalog.columns:
            df_filtered = df_catalog[df_catalog["Family"].isin(selected_io_types)].copy()
            print(f"[ModuleSelector] After Family filter: {len(df_filtered)} modules (selected: {selected_io_types})")
            print(f"[ModuleSelector] Sample Family values: {df_catalog['Family'].unique()[:5]}")
            return df_filtered
        else:
            print(f"[ModuleSelector] WARNING: 'Family' column not found. Available columns: {list(df_catalog.columns)}")
            return df_catalog

    @staticmethod
    def filter_modules_by_io_type(df_modules: pd.DataFrame) -> pd.DataFrame:
        """
        Filter modules by IO_Type column (AI, DI, DO, AO).
        Excludes SOFT type signals.
        
        Args:
            df_modules: Filtered modules DataFrame (after Family filter)
            
        Returns:
            Filtered DataFrame with only AI, DI, DO, AO IO types (SOFT excluded)
        """
        if "IO_Type" not in df_modules.columns:
            print(f"[ModuleSelector] WARNING: 'IO_Type' column not found. Available columns: {list(df_modules.columns)}")
            return df_modules
        
        # Keep only main IO types (exclude SOFT)
        valid_io_types = ["AI", "DI", "DO", "AO"]
        io_type_count = len(df_modules)
        
        df_filtered = df_modules[df_modules["IO_Type"].isin(valid_io_types)].copy()
        print(f"[ModuleSelector] After IO_Type filter: {len(df_filtered)} modules (removed {io_type_count - len(df_filtered)})")
        print(f"[ModuleSelector] IO_Type distribution: {df_filtered['IO_Type'].value_counts().to_dict()}")
        
        return df_filtered

    @staticmethod
    def apply_default_constraints(df_modules: pd.DataFrame) -> pd.DataFrame:
        """
        Apply default constraints:
        - Supports_HART: Yes (only for AI type)
        - Wiring: 2-wire (only for AI type)
        
        Args:
            df_modules: Filtered modules DataFrame
            
        Returns:
            DataFrame with default constraints applied
        """
        df_filtered = df_modules.copy()
        print(f"[ModuleSelector] Before constraints: {len(df_filtered)} modules")
        
        # HART and Wiring constraints only apply to AI type modules
        # DI, DO, AO modules do not have HART/Wiring requirements
        
        if "IO_Type" in df_filtered.columns:
            # Separate AI and non-AI modules
            ai_modules = df_filtered[df_filtered["IO_Type"] == "AI"].copy()
            non_ai_modules = df_filtered[df_filtered["IO_Type"] != "AI"].copy()
            
            print(f"[ModuleSelector] Separating AI ({len(ai_modules)}) and non-AI modules ({len(non_ai_modules)})")
            
            # Apply HART and Wiring constraints only to AI modules
            if len(ai_modules) > 0:
                print(f"[ModuleSelector] Applying HART/Wiring constraints to AI modules...")
                
                # Filter AI for HART support = Yes
                if "Supports_HART" in ai_modules.columns:
                    hart_count = len(ai_modules)
                    ai_modules = ai_modules[ai_modules["Supports_HART"].astype(str).str.upper() == "YES"]
                    print(f"[ModuleSelector]   After HART filter (AI only): {len(ai_modules)} modules (removed {hart_count - len(ai_modules)})")
                    if hart_count > len(ai_modules):
                        print(f"[ModuleSelector]   Sample HART values: {df_filtered[df_filtered['IO_Type']=='AI']['Supports_HART'].unique()[:5]}")
                
                # Filter AI for 2-wire wiring
                if "Wiring" in ai_modules.columns:
                    wire_count = len(ai_modules)
                    ai_modules = ai_modules[ai_modules["Wiring"].astype(str).str.strip() == "2-wire"]
                    print(f"[ModuleSelector]   After Wiring filter (AI only): {len(ai_modules)} modules (removed {wire_count - len(ai_modules)})")
                    if wire_count > len(ai_modules):
                        print(f"[ModuleSelector]   Sample Wiring values: {df_filtered[df_filtered['IO_Type']=='AI']['Wiring'].unique()[:5]}")
            
            # Combine AI (with constraints applied) and non-AI modules
            df_filtered = pd.concat([ai_modules, non_ai_modules], ignore_index=True)
            print(f"[ModuleSelector] After HART/Wiring constraints: {len(df_filtered)} modules total")
        else:
            print(f"[ModuleSelector] WARNING: 'IO_Type' column not found for conditional constraint filtering")
        
        return df_filtered

    @staticmethod
    def apply_temperature_constraint(df_modules: pd.DataFrame, temperature_rating: Optional[str]) -> pd.DataFrame:
        """
        Apply temperature rating constraint.
        If temperature_rating is "Standard", select modules with Ambient_Max_C < 70.
        
        Args:
            df_modules: Modules DataFrame
            temperature_rating: User selected temperature rating (e.g., "Standard", "High", "Extended")
            
        Returns:
            Filtered DataFrame based on temperature constraint
        """
        df_filtered = df_modules.copy()
        
        if temperature_rating and temperature_rating.upper() == "STANDARD":
            if "Ambient_Max_C" in df_filtered.columns:
                temp_count = len(df_filtered)
                # Convert to numeric, handling any non-numeric values
                df_filtered["Ambient_Max_C"] = pd.to_numeric(df_filtered["Ambient_Max_C"], errors="coerce")
                df_filtered = df_filtered[df_filtered["Ambient_Max_C"] < 70]
                print(f"[ModuleSelector] After Temperature filter (Standard, < 70°C): {len(df_filtered)} modules (removed {temp_count - len(df_filtered)})")
                if temp_count > len(df_filtered):
                    print(f"[ModuleSelector] Sample Ambient_Max_C values: {df_modules['Ambient_Max_C'].unique()[:5]}")
            else:
                print(f"[ModuleSelector] WARNING: 'Ambient_Max_C' column not found")
        else:
            print(f"[ModuleSelector] No temperature constraint applied (rating: {temperature_rating})")
        
        return df_filtered

    @staticmethod
    def get_available_modules(
        excel_path: str,
        selected_io_types: List[str],
        temperature_rating: Optional[str] = None,
        required_io_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Main method to get available modules based on constraints.
        Returns DataFrame with Module, IO_Type, and Usable_Channels for further processing.
        
        Args:
            excel_path: Path to the Yokogawa constraints Excel file
            selected_io_types: List of selected IO types (e.g., ["FIO"])
            temperature_rating: User selected temperature rating (default: None)
            required_io_types: Optional list of IO_Types (AI/DI/DO/AO) that must be present in the result
            
        Returns:
            DataFrame with columns {Module, IO_Type, Usable_Channels, Family, Ambient_Max_C}
        """
        try:
            print(f"\n[ModuleSelector] Starting module selection...")
            print(f"[ModuleSelector] Selected IO Types: {selected_io_types}")
            print(f"[ModuleSelector] Temperature Rating: {temperature_rating}")
            if required_io_types:
                print(f"[ModuleSelector] Required IO Types (from signals): {required_io_types}")
            
            # Step 1: Load module catalog
            df_catalog = ModuleSelector.load_module_catalog_from_excel(excel_path)
            print(f"[ModuleSelector] Total modules in catalog: {len(df_catalog)}")
            print(f"[ModuleSelector] Columns available: {list(df_catalog.columns)}")
            
            # Step 2: Filter by IO Family
            df_filtered = ModuleSelector.filter_modules_by_io_family(df_catalog, selected_io_types)
            
            # Step 3: Filter by IO_Type (AI, DI, DO, AO - excluding SOFT)
            df_filtered = ModuleSelector.filter_modules_by_io_type(df_filtered)
            
            # Step 4: Apply default constraints (HART, Wiring)
            df_filtered = ModuleSelector.apply_default_constraints(df_filtered)
            
            # Step 5: Apply temperature constraint
            df_filtered = ModuleSelector.apply_temperature_constraint(df_filtered, temperature_rating)
            
            # Ensure required IO types are present (so signals like DO/Redundant are not dropped)
            if required_io_types:
                required_upper = {str(x).strip().upper() for x in required_io_types if x}
                present_upper = {str(x).strip().upper() for x in df_filtered.get('IO_Type', []).dropna().unique()}
                missing = required_upper - present_upper
                if missing:
                    print(f"[ModuleSelector] WARNING: Required IO types missing after filtering: {sorted(missing)}")
                    # Add missing IO types from the original catalog (without family filtering)
                    missing_rows = df_catalog[df_catalog['IO_Type'].astype(str).str.strip().str.upper().isin(missing)]
                    if not missing_rows.empty:
                        print(f"[ModuleSelector] Including {len(missing_rows)} missing module(s) for required IO types")
                        df_filtered = pd.concat([df_filtered, missing_rows], ignore_index=True)
                    else:
                        print(f"[ModuleSelector] WARNING: No modules found in catalog for missing IO types: {sorted(missing)}")
            
            print(f"[ModuleSelector] Final result: {len(df_filtered)} modules after all filters\n")
            
            # Step 6: Keep only required columns and return as DataFrame
            result_df = df_filtered[["Module", "IO_Type", "Usable_Channels"]].copy()
            if "Family" in df_filtered.columns:
                result_df["Family"] = df_filtered["Family"]
            if "Ambient_Max_C" in df_filtered.columns:
                result_df["Ambient_Max_C"] = df_filtered["Ambient_Max_C"]
            
            return result_df
        
        except Exception as e:
            raise Exception(f"Error getting available modules: {str(e)}")

    @staticmethod
    def get_module_channels_summary(available_modules: List[Dict]) -> Dict[str, int]:
        """
        Get summary of total usable channels by module.
        
        Args:
            available_modules: List of available modules from get_available_modules()
            
        Returns:
            Dictionary mapping module names to usable channels
        """
        summary = {}
        for module in available_modules:
            module_name = module.get("Module", "Unknown")
            channels = module.get("Usable_Channels", 0)
            summary[module_name] = channels
        
        return summary
