"""Bill of Materials (BOM) domain logic.

This module provides core BOM generation logic based on allocation results and
the Yokogawa constraints workbook.

It is intentionally lightweight and focused on generating a simple module
quantity summary with descriptions pulled from the IO_Module_Catalog sheet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from domain.services.module_selector import ModuleSelector


class BillOfMaterials:
    """Domain logic for generating a Bill of Materials from allocation results."""

    @staticmethod
    def generate_from_design_input(
        design_input_results: Dict,
        constraints_file: Optional[str] = None,
        logger_callback=None
    ) -> pd.DataFrame:
        """Generate a BOM DataFrame from design input results.

        This produces a table of module names, total quantities, and module
        descriptions (pulled from the IO_Module_Catalog sheet in the constraints
        workbook).

        Args:
            design_input_results: The output of DesignInputReviewService.process_design_input()
            constraints_file: Optional path to the Yokogawa constraints Excel file.
                If omitted, the default template path is used.
            logger_callback: Optional logging callback.

        Returns:
            DataFrame with columns [Module, Description, Total Quantity, Single_Modules, Dual_Red_Modules]
        """
        # Determine module summary from design input results
        module_summary = design_input_results.get("module_summary")
        if module_summary is None or (isinstance(module_summary, pd.DataFrame) and module_summary.empty):
            if logger_callback:
                logger_callback("BOM: No module summary available; returning empty BOM.")
            return pd.DataFrame(columns=["Module", "Description", "Total Quantity", "Single_Modules", "Dual_Red_Modules"])

        # Ensure module_summary is a DataFrame
        module_summary_df = module_summary.copy() if isinstance(module_summary, pd.DataFrame) else pd.DataFrame(module_summary)

        # Normalize module name and quantity columns
        for col in ["Module", "Total_FIO_Modules", "Single_Modules", "Dual_Red_Modules"]:
            if col not in module_summary_df.columns:
                module_summary_df[col] = 0

        module_summary_df["Module"] = module_summary_df["Module"].astype(str).str.strip()

        # Aggregate quantities by module name
        bom_df = (
            module_summary_df
            .groupby("Module", dropna=False, as_index=False)
            .agg({
                "Total_FIO_Modules": "sum",
                "Single_Modules": "sum",
                "Dual_Red_Modules": "sum",
            })
            .rename(columns={"Total_FIO_Modules": "Total Quantity"})
        )

        # Load module catalog to get descriptions
        if constraints_file is None:
            base_path = Path(__file__).resolve().parents[2]
            constraints_file = str(base_path / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx")

        try:
            catalog_df = ModuleSelector.load_module_catalog_from_excel(str(constraints_file))
            if "Module" in catalog_df.columns and "Description" in catalog_df.columns:
                catalog_desc = catalog_df[["Module", "Description"]].drop_duplicates().copy()
                catalog_desc["Module"] = catalog_desc["Module"].astype(str).str.strip()
                bom_df = bom_df.merge(catalog_desc, on="Module", how="left")
            else:
                bom_df["Description"] = ""
        except Exception as e:
            if logger_callback:
                logger_callback(f"BOM: Failed to load module catalog for descriptions: {e}")
            bom_df["Description"] = ""

        # Ensure columns exist and are ordered predictably
        for col in ["Description", "Total Quantity", "Single_Modules", "Dual_Red_Modules"]:
            if col not in bom_df.columns:
                bom_df[col] = 0 if col != "Description" else ""

        # Prefer a stable sort order for the BOM output and ensure consistent column ordering
        bom_df = bom_df.sort_values(by=["Module"]).reset_index(drop=True)
        bom_df = bom_df[["Module", "Description", "Single_Modules", "Dual_Red_Modules", "Total Quantity"]]

        return bom_df
