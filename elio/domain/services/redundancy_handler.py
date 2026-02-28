"""Redundancy handling services."""
import re
from copy import deepcopy
from typing import Optional


class RedundancyHandler:
    """Module-level redundancy handler - duplicates modules for redundancy."""

    @staticmethod
    def apply(modules):
        redundant_modules = []

        for m in modules:
            redundant_modules.append(m)
            backup = deepcopy(m)
            redundant_modules.append(backup)

        return redundant_modules


class RedundancyClassifier:
    """
    Classifies redundancy values from Excel into standardized format.
    Handles various input formats:
        - Yes/No, Y/N
        - True/False, T/F
        - 1/0
        - Redundant/Non-Redundant, R/NR
        - Redundant/Non_Redundant, Redundant/Non-Redundant
    """

    # Redundant indicators (affirmative values) - UPPERCASE since input is converted to uppercase
    REDUNDANT_PATTERNS = [
        r"^Y(?:ES)?$",          # Y, YES
        r"^T(?:RUE)?$",         # T, TRUE
        r"^1$",                 # 1
        r"^R(?:EDUNDANT)?$",    # R, REDUNDANT
        r"^REDUNDANT",          # REDUNDANT (any variation)
    ]

    # Non-redundant indicators (negative values) - UPPERCASE since input is converted to uppercase
    NON_REDUNDANT_PATTERNS = [
        r"^N(?:O)?$",           # N, NO
        r"^F(?:ALSE)?$",        # F, FALSE
        r"^0$",                 # 0
        r"^NR$",                # NR
        r"^NON[-_]?REDUNDANT",  # NON-REDUNDANT, NON_REDUNDANT
    ]

    @staticmethod
    def _classify_value(redundancy_value: str) -> Optional[str]:
        """
        Classify a redundancy value to either "Redundant", "Non-Redundant", or None.
        
        Args:
            redundancy_value: String value from IO_REDUNDANCY column
            
        Returns:
            "Redundant", "Non-Redundant", or None if unrecognized
        """
        if not redundancy_value:
            return None
        
        # Convert to string, strip, uppercase for matching
        value_str = str(redundancy_value).strip().upper()
        
        if not value_str:
            return None
        
        # Check against redundant patterns
        for pattern in RedundancyClassifier.REDUNDANT_PATTERNS:
            if re.match(pattern, value_str):
                return "Redundant"
        
        # Check against non-redundant patterns
        for pattern in RedundancyClassifier.NON_REDUNDANT_PATTERNS:
            if re.match(pattern, value_str):
                return "Non-Redundant"
        
        # If no pattern matches, return None (unrecognized value)
        return None

    @staticmethod
    def classify(redundancy_value: str) -> Optional[str]:
        """
        Classify redundancy value.
        
        Args:
            redundancy_value: Raw value from IO_REDUNDANCY column
            
        Returns:
            "Redundant", "Non-Redundant", or None
        """
        return RedundancyClassifier._classify_value(redundancy_value)

    @staticmethod
    def is_redundant(redundancy_value: str) -> bool:
        """
        Check if a redundancy value indicates redundant status.
        
        Returns:
            True if redundant, False otherwise
        """
        classified = RedundancyClassifier.classify(redundancy_value)
        return classified == "Redundant"

    @staticmethod
    def is_non_redundant(redundancy_value: str) -> bool:
        """
        Check if a redundancy value indicates non-redundant status.
        
        Returns:
            True if non-redundant, False otherwise
        """
        classified = RedundancyClassifier.classify(redundancy_value)
        return classified == "Non-Redundant"