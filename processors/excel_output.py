"""
Excel Output Generator
Handles all Excel file output generation for channel assignments and module allocations.
"""

import pandas as pd
import logging
from typing import Dict, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class ExcelOutputGenerator:
    """Generates Excel output files for channel assignments and module allocations."""
    
    def __init__(self, logger=None):
        """
        Initialize the Excel output generator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    
    def write_assignment_to_excel(self, 
                                  output_file_path: str,
                                  df_assignment: pd.DataFrame,
                                  assignment_table: pd.DataFrame) -> bool:
        """
        Write channel assignments to Excel file.
        
        Creates two sheets:
        1. Signal_Assignments: Individual signal-to-channel mappings
        2. Module_Allocation: Module capacity and utilization details
        
        Args:
            output_file_path (str): Path to output Excel file
            df_assignment (pd.DataFrame): DataFrame with signal-to-channel assignments
            assignment_table (pd.DataFrame): Module allocation table
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            wb = Workbook()
            wb.remove(wb.active)
            
            # Sheet 1: Signal Assignments
            ws_signals = wb.create_sheet('Signal_Assignments', 0)
            headers = ['PID_TAG', 'Description', 'IO_Type', 'Module_Name', 'Channel', 
                      'Node', 'Slot', 'Signal_Type', 'Utilization']
            
            self._write_sheet_headers(ws_signals, headers)
            
            for row_idx, row in df_assignment.iterrows():
                for col_idx, header in enumerate(headers, 1):
                    cell = ws_signals.cell(row=row_idx+2, column=col_idx)
                    cell.value = row.get(header, '')
                    cell.alignment = Alignment(horizontal="left", vertical="center")
            
            self._auto_adjust_columns(ws_signals)
            
            # Sheet 2: Module Allocation
            ws_modules = wb.create_sheet('Module_Allocation', 1)
            module_headers = list(assignment_table.columns)
            
            self._write_sheet_headers(ws_modules, module_headers)
            
            for row_idx, row in assignment_table.iterrows():
                for col_idx, header in enumerate(module_headers, 1):
                    cell = ws_modules.cell(row=row_idx+2, column=col_idx)
                    cell.value = row.get(header, '')
                    cell.alignment = Alignment(horizontal="left", vertical="center")
            
            self._auto_adjust_columns(ws_modules)
            
            wb.save(output_file_path)
            self.logger.info(f"Assignment file written: {output_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing assignment file: {e}")
            raise
    
    
    def _write_sheet_headers(self, worksheet, headers: list):
        """Write headers with formatting to worksheet."""
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
    
    
    def _auto_adjust_columns(self, worksheet):
        """Auto-adjust column widths based on content."""
        for col in worksheet.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            worksheet.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)
    
    
    def write_distribution_summary_to_excel(self,
                                           output_file_path: str,
                                           distribution_plan: Dict[str, dict],
                                           mount_table: pd.DataFrame = None) -> bool:
        """
        Write distribution summary to Excel file.
        
        Args:
            output_file_path (str): Path to output Excel file
            distribution_plan (Dict[str, dict]): Distribution plan per IO type
            mount_table (pd.DataFrame): Optional mounting table
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            wb = Workbook()
            wb.remove(wb.active)
            
            # Sheet 1: Distribution Summary
            ws_summary = wb.create_sheet('Distribution_Summary', 0)
            summary_headers = ['IO_Type', 'Module_Name', 'Signals', 'Wired_Spares', 
                              'Blank_Channels', 'Total_Items', 'Modules_Required', 
                              'Channels_Per_Module', 'Total_Available', 'Utilization_%']
            
            self._write_sheet_headers(ws_summary, summary_headers)
            
            row_idx = 2
            for io_type in sorted(distribution_plan.keys()):
                plan = distribution_plan[io_type]
                utilization = round((plan['total_items'] / plan['total_available_channels'] * 100), 1) \
                    if plan['total_available_channels'] > 0 else 0
                
                data = [
                    io_type,
                    plan['module_name'],
                    plan['signals'],
                    plan['wired_spares'],
                    plan['blank_channels'],
                    plan['total_items'],
                    plan['modules_required'],
                    plan['channels_per_module'],
                    plan['total_available_channels'],
                    utilization
                ]
                
                for col_idx, value in enumerate(data, 1):
                    cell = ws_summary.cell(row=row_idx, column=col_idx)
                    cell.value = value
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                
                row_idx += 1
            
            self._auto_adjust_columns(ws_summary)
            
            # Sheet 2: Module Details
            ws_modules = wb.create_sheet('Module_Details', 1)
            module_headers = ['IO_Type', 'Module_Instance', 'Module_Index', 'Signals', 
                             'Wired_Spares', 'Blank_Channels', 'Total_Items', 'Capacity', 'Utilization_%']
            
            self._write_sheet_headers(ws_modules, module_headers)
            
            row_idx = 2
            for io_type in sorted(distribution_plan.keys()):
                plan = distribution_plan[io_type]
                for spec in plan['module_specs']:
                    util = round((spec['total_items'] / spec['capacity'] * 100), 1) \
                        if spec['capacity'] > 0 else 0
                    
                    data = [
                        io_type,
                        spec['module_instance'],
                        spec['module_index'],
                        spec['signals'],
                        spec['wired_spares'],
                        spec['blank_channels'],
                        spec['total_items'],
                        spec['capacity'],
                        util
                    ]
                    
                    for col_idx, value in enumerate(data, 1):
                        cell = ws_modules.cell(row=row_idx, column=col_idx)
                        cell.value = value
                        cell.alignment = Alignment(horizontal="left", vertical="center")
                    
                    row_idx += 1
            
            self._auto_adjust_columns(ws_modules)
            
            # Sheet 3: Mounting Table (if provided)
            if mount_table is not None:
                ws_mount = wb.create_sheet('Mounting_Table', 2)
                
                # Write headers (column names)
                for col_idx, col_name in enumerate(mount_table.columns, 1):
                    cell = ws_mount.cell(row=1, column=col_idx)
                    cell.value = col_name
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                
                # Write row index (node names) in column A
                for row_idx, row_name in enumerate(mount_table.index, 1):
                    cell = ws_mount.cell(row=row_idx+1, column=1)
                    cell.value = row_name
                    cell.font = Font(bold=True)
                
                # Write data
                for row_idx, (_, row_data) in enumerate(mount_table.iterrows(), 2):
                    for col_idx, value in enumerate(row_data, 2):
                        cell = ws_mount.cell(row=row_idx, column=col_idx)
                        cell.value = value
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                
                self._auto_adjust_columns(ws_mount)
            
            wb.save(output_file_path)
            self.logger.info(f"Distribution summary file written: {output_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing distribution summary file: {e}")
            raise
