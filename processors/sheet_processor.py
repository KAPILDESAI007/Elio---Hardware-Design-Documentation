from abc import ABC, abstractmethod
from pathlib import Path
import logging
import pandas as pd
import re

logger = logging.getLogger("CloudAppLogger")

class SheetProcessor(ABC):
    """
    Base class for processing Excel sheets.
    Provides common functionality for reading, validating, and processing spreadsheets.
    """
    
    # Valid IO types that can be used in the system
    VALID_IO_TYPES = ['AI', 'DI', 'DO', 'AO', 'SOFT']
    
    def __init__(self, workbook_path: Path, sheet_name: str, df_points):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.df_points = df_points

    @abstractmethod
    def process(self):
        pass

    def _save_workbook(self, wb):
        """Save workbook to disk"""
        try:
            wb.save(self.workbook_path)
            logger.debug(f"Workbook saved: {self.workbook_path}")
        except Exception as e:
            logger.error(f"Failed to save workbook: {e}")
            raise
        finally:
            try:
                wb.close()
            except Exception:
                pass

    # ===================== FILE READING METHODS =====================
    
    def read_excel_file(self, file_path: Path, sheet_name: str = None) -> pd.DataFrame:
        """
        Read Excel file and return DataFrame.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Specific sheet to read (optional)
        
        Returns:
            DataFrame if successful, None otherwise
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file reading fails
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Excel file not found: {file_path}")
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"Reading Excel file: {file_path}")
            
            # Read Excel file
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                logger.info(f"Successfully read sheet '{sheet_name}' from {file_path.name}")
            else:
                df = pd.read_excel(file_path)
                logger.info(f"Successfully read Excel file: {file_path.name}")
            
            logger.debug(f"DataFrame shape: {df.shape}")
            logger.debug(f"Columns: {list(df.columns)}")
            
            return df
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            raise

    def check_columns_exist(self, df: pd.DataFrame, required_columns: list) -> dict:
        """
        Check if all required columns exist in DataFrame.
        
        Args:
            df: DataFrame to check
            required_columns: List of required column names
        
        Returns:
            Dictionary with check results:
            {
                'success': bool,
                'available_columns': list,
                'missing_columns': list,
                'total_columns': int
            }
        """
        try:
            if df is None or df.empty:
                logger.warning("DataFrame is empty or None")
                return {
                    'success': False,
                    'available_columns': [],
                    'missing_columns': required_columns,
                    'total_columns': 0,
                    'error': 'DataFrame is empty or None'
                }
            
            # Normalize column names (strip whitespace, uppercase)
            available_cols = [str(col).strip() for col in df.columns]
            required_cols_normalized = [str(col).strip() for col in required_columns]
            
            # Check which columns are missing
            missing = [col for col in required_cols_normalized if col.upper() not in [c.upper() for c in available_cols]]
            
            all_available = len(missing) == 0
            
            logger.info(f"Column check: {len(required_cols_normalized)} required, {len(available_cols)} available")
            if missing:
                logger.warning(f"Missing columns: {missing}")
            else:
                logger.info("All required columns are available")
            
            return {
                'success': all_available,
                'available_columns': available_cols,
                'missing_columns': missing,
                'total_columns': len(available_cols),
                'required_columns_count': len(required_cols_normalized)
            }
            
        except Exception as e:
            logger.error(f"Error checking columns: {e}")
            return {
                'success': False,
                'available_columns': [],
                'missing_columns': required_columns,
                'total_columns': 0,
                'error': str(e)
            }

    # ===================== IO TYPE VALIDATION METHODS =====================
    
    def validate_io_types(self, df: pd.DataFrame, io_type_column: str = 'IO_type') -> dict:
        """
        Validate that all IO types in DataFrame are valid categories.
        Valid types: AI, DI, DO, AO, SOFT
        
        Args:
            df: DataFrame containing IO type data
            io_type_column: Name of column containing IO types
        
        Returns:
            Dictionary with validation results:
            {
                'success': bool,
                'valid_io_types': list,
                'invalid_io_types': list,
                'categorization': dict (AI: count, DI: count, etc.),
                'total_rows': int,
                'errors': list
            }
        """
        try:
            if df is None or df.empty:
                logger.warning("DataFrame is empty or None")
                return {
                    'success': False,
                    'valid_io_types': [],
                    'invalid_io_types': [],
                    'categorization': {},
                    'total_rows': 0,
                    'errors': ['DataFrame is empty or None']
                }
            
            # Check if column exists
            if io_type_column not in df.columns:
                logger.error(f"IO type column '{io_type_column}' not found in DataFrame")
                logger.info(f"Available columns: {list(df.columns)}")
                return {
                    'success': False,
                    'valid_io_types': [],
                    'invalid_io_types': [],
                    'categorization': {},
                    'total_rows': len(df),
                    'errors': [f"Column '{io_type_column}' not found"]
                }
            
            # Extract and normalize IO types
            io_types_raw = df[io_type_column].astype(str).str.upper().str.strip()
            unique_io_types = io_types_raw.unique()
            
            valid_types = []
            invalid_types = []
            categorization = {io_type: 0 for io_type in self.VALID_IO_TYPES}
            categorization['INVALID'] = 0
            
            # Validate each unique IO type
            for io_type in unique_io_types:
                io_type_base = self._extract_io_type_base(io_type)
                
                if io_type_base in self.VALID_IO_TYPES:
                    valid_types.append(io_type_base)
                else:
                    invalid_types.append(io_type)
            
            # Count each type in the DataFrame
            for idx, row_io_type in enumerate(io_types_raw):
                base_type = self._extract_io_type_base(row_io_type)
                if base_type in self.VALID_IO_TYPES:
                    categorization[base_type] += 1
                else:
                    categorization['INVALID'] += 1
            
            # Remove categories with zero count (except INVALID which will be deleted if 0)
            categorization = {k: v for k, v in categorization.items() if v > 0}
            
            # Note: INVALID is only in categorization if count > 0
            
            success = len(invalid_types) == 0
            
            logger.info(f"IO Type Validation: {len(valid_types)} valid types, {len(invalid_types)} invalid types")
            logger.info(f"Categorization: {categorization}")
            
            if invalid_types:
                logger.warning(f"Invalid IO types found: {set(invalid_types)}")
            else:
                logger.info("All IO types are valid")
            
            return {
                'success': success,
                'valid_io_types': list(set(valid_types)),
                'invalid_io_types': list(set(invalid_types)),
                'categorization': categorization,
                'total_rows': len(df),
                'errors': [] if success else [f"Invalid IO types found: {set(invalid_types)}"]
            }
            
        except Exception as e:
            logger.error(f"Error validating IO types: {e}")
            return {
                'success': False,
                'valid_io_types': [],
                'invalid_io_types': [],
                'categorization': {},
                'total_rows': len(df) if df is not None else 0,
                'errors': [str(e)]
            }

    @staticmethod
    def _extract_io_type_base(io_type_str):
        """
        Extract base IO type (AI, DI, DO, AO, SOFT) from IO type string.
        
        Examples:
            'AI-R' -> 'AI'
            'DI' -> 'DI'
            'AO-2W' -> 'AO'
            'SOFT' -> 'SOFT'
            'SOFTWARE' -> 'SOFT'
        
        Args:
            io_type_str: Raw IO type string
        
        Returns:
            Base IO type string or original string if no match
        """
        io_type_upper = str(io_type_str).upper().strip()
        
        # Check for SOFT variations first
        if re.search(r'SOFT|SOFTWARE', io_type_upper):
            return 'SOFT'
        
        # Look for AI, DI, DO, AO
        base_types = ['AI', 'DI', 'DO', 'AO']
        for base_type in base_types:
            match = re.search(r'\b' + base_type + r'\b', io_type_upper)
            if match:
                return base_type
        
        # If no match found, return the original string
        return io_type_upper
