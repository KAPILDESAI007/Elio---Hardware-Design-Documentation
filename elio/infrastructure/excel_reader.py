import pandas as pd
from typing import List, Dict, Optional
from domain.models.signal import Signal
from domain.services.signal_classifier import SignalClassifier
from domain.services.redundancy_handler import RedundancyClassifier
from settings import EXCEL_COLUMN_MAPPING


class ExcelReader:

    @staticmethod
    def _find_column(df: pd.DataFrame, column_aliases: List[str]) -> Optional[str]:
        """
        Find the actual column name in dataframe by checking aliases.
        Returns the first matching column name or None if not found.
        """
        for alias in column_aliases:
            if alias in df.columns:
                return alias
        return None

    @staticmethod
    def _get_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Create a mapping of signal attributes to actual excel column names
        for the current dataframe. Uses EXCEL_COLUMN_MAPPING from settings.
        """
        mapping = {}
        for signal_attr, aliases in EXCEL_COLUMN_MAPPING.items():
            actual_col = ExcelReader._find_column(df, aliases)
            mapping[signal_attr] = actual_col
        return mapping

    @staticmethod
    def _handle_nan_value(value):
        """
        Convert NaN values to None for proper Pydantic validation.
        Handles pandas NaN from empty Excel cells.
        """
        if pd.isna(value):
            return None
        # Convert to string and strip whitespace, return None if empty
        str_value = str(value).strip()
        return str_value if str_value else None

    @staticmethod
    def read(file) -> List[Signal]:
        """
        Read excel file and create Signal objects.
        Handles configurable column names for different excel formats.
        Properly handles NaN values from blank cells.
        """
        df = pd.read_excel(file)

        # Get the column mapping for this dataframe
        column_mapping = ExcelReader._get_column_mapping(df)

        # Verify required columns are present
        if not column_mapping.get("tag"):
            raise ValueError("Required column 'tag' not found. Available columns: {}".format(list(df.columns)))
        if not column_mapping.get("signal_type"):
            raise ValueError("Required column 'signal_type' not found. Available columns: {}".format(list(df.columns)))

        signals = []
        for _, row in df.iterrows():
            raw_signal_type = ExcelReader._handle_nan_value(row[column_mapping["signal_type"]])
            
            # Classify signal type to one of: AI, DI, DO, AO, SOFT
            classified_signal_type = SignalClassifier.classify(raw_signal_type) if raw_signal_type else None
            
            signal_data = {
                "tag": ExcelReader._handle_nan_value(row[column_mapping["tag"]]),
                "signal_type": classified_signal_type,
            }

            # Add optional Design Input Review fields - always handle NaN
            if column_mapping.get("pid_tag"):
                signal_data["pid_tag"] = ExcelReader._handle_nan_value(row[column_mapping["pid_tag"]])
            if column_mapping.get("signal_origin"):
                signal_data["signal_origin"] = ExcelReader._handle_nan_value(row[column_mapping["signal_origin"]])
            if column_mapping.get("io_redundancy"):
                raw_redundancy = ExcelReader._handle_nan_value(row[column_mapping["io_redundancy"]])
                # Classify redundancy value to "Redundant" or "Non-Redundant"
                signal_data["io_redundancy"] = RedundancyClassifier.classify(raw_redundancy) if raw_redundancy else None
            if column_mapping.get("is_non_is"):
                signal_data["is_non_is"] = ExcelReader._handle_nan_value(row[column_mapping["is_non_is"]])
            if column_mapping.get("jb_cable_name"):
                signal_data["jb_cable_name"] = ExcelReader._handle_nan_value(row[column_mapping["jb_cable_name"]])
            if column_mapping.get("spare_channel_requirement"):
                signal_data["spare_channel_requirement"] = ExcelReader._handle_nan_value(row[column_mapping["spare_channel_requirement"]])

            signals.append(Signal(**signal_data))

        return signals

    @staticmethod
    def get_available_columns(file) -> Dict[str, Optional[str]]:
        """
        Utility method to check what columns were found in the excel file.
        Useful for debugging and understanding the column mapping.
        """
        df = pd.read_excel(file)
        return ExcelReader._get_column_mapping(df)