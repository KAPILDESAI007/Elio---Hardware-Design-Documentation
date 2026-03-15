"""Signal classifier service - Classifies signals into main types."""
import re
from typing import Dict, Optional


class SignalClassifier:
    """
    Classifies signals into 5 main types: AI, DI, DO, AO, SOFT
    Handles variations like:
        - Short forms: AI, DI, DO, AO, SOFT
        - Short with modifiers: AI-R, AI_REDUNDANT, DI-1, etc.
        - Full names: Analog Input, Digital Input, Digital Output, Analog Output
        - Mixed case/separators: analog_input, Analog-Input, ANALOG INPUT, etc.
    """

    # Main signal types
    SIGNAL_TYPES = ["AI", "DI", "DO", "AO", "SOFT"]

    # Pattern mappings for each signal type (order matters - more specific first)
    PATTERN_MAP = {
        "AI": [
            r"^AI(?:[-_\s]|$)",  # AI, AI-, AI_, AI space
            r"^A\.?I(?:[-_\s]|$)",  # A.I, A-I, etc.
            r"analog[-_\s]?input",  # Analog Input, Analog-Input, Analog_Input
        ],
        "DI": [
            r"^DI(?:[-_\s]|$)",  # DI, DI-, DI_, DI space
            r"^D\.?I(?:[-_\s]|$)",  # D.I, D-I, etc.
            r"digital[-_\s]?input",  # Digital Input, Digital-Input, Digital_Input
        ],
        "DO": [
            r"^DO(?:[-_\s]|$)",  # DO, DO-, DO_, DO space
            r"^D\.?O(?:[-_\s]|$)",  # D.O, D-O, etc.
            r"digital[-_\s]?output",  # Digital Output, Digital-Output, Digital_Output
        ],
        "AO": [
            r"^AO(?:[-_\s]|$)",  # AO, AO-, AO_, AO space
            r"^A\.?O(?:[-_\s]|$)",  # A.O, A-O, etc.
            r"analog[-_\s]?output",  # Analog Output, Analog-Output, Analog_Output
        ],
        "SOFT": [
            r"^SOFT(?:[-_\s]|$)",  # SOFT, SOFT-, SOFT_, SOFT space
            r"software",  # Sometimes referred as "software"
            r"soft[-_\s]?signal",  # Soft Signal, Soft-Signal, etc.
        ],
    }

    @staticmethod
    def _extract_base_type(signal_type_str: str) -> Optional[str]:
        """
        Extract base signal type from various formats.
        
        Examples:
            'AI' -> 'AI'
            'AI-R' -> 'AI'
            'Analog Input' -> 'AI'
            'analog_input' -> 'AI'
            'Digital-Output' -> 'DO'
            'DI-Redundant' -> 'DI'
            'SOFT' -> 'SOFT'
            'unknown_signal' -> None
            '' -> None
            
        Returns:
            Base signal type (AI, DI, DO, AO, SOFT) or None if not found
        """
        if not signal_type_str:
            return None
        
        # Convert to uppercase and strip whitespace
        signal_str = str(signal_type_str).strip().upper()
        
        if not signal_str:
            return None
        
        # Check each signal type's patterns
        for signal_type, patterns in SignalClassifier.PATTERN_MAP.items():
            for pattern in patterns:
                if re.search(pattern, signal_str):
                    return signal_type
        
        # If no pattern matches, return None (unknown/unclassified)
        return None

    @staticmethod
    def classify(signal_type_str: str) -> Optional[str]:
        """
        Classify a signal type string into one of the 5 main types.
        
        Args:
            signal_type_str: Signal type string (may contain variations, or be None/empty)
            
        Returns:
            Classified signal type (AI, DI, DO, AO, SOFT) or None if unclassifiable
        """
        return SignalClassifier._extract_base_type(signal_type_str)

    @staticmethod
    def normalize_redundancy_status(value) -> str:
        """Normalize various redundancy indicators into 'Redundant' or 'Non-Redundant'."""
        if value is None:
            return "Non-Redundant"
        if isinstance(value, bool):
            return "Redundant" if value else "Non-Redundant"
        v = str(value).strip().upper()
        if not v:
            return "Non-Redundant"
        if v in ["R", "RED", "REDUNDANT", "YES", "Y", "TRUE", "1"]:
            return "Redundant"
        return "Non-Redundant"

    @staticmethod
    def normalize_is_status(value) -> str:
        """Normalize various IS/Non-IS indicators into 'IS' or 'Non-IS'."""
        if value is None:
            return "Non-IS"
        if isinstance(value, bool):
            return "IS" if value else "Non-IS"
        v = str(value).strip().upper()
        if not v:
            return "Non-IS"
        if v.startswith("IS"):
            return "IS"
        if v.startswith("NIS") or v.startswith("NON"):
            return "Non-IS"
        return "Non-IS"

    @staticmethod
    def is_valid_signal_type(signal_type: str) -> bool:
        """Check if a signal type is one of the 5 main types"""
        return signal_type in SignalClassifier.SIGNAL_TYPES

    @staticmethod
    def get_all_signal_types() -> list:
        """Return list of all valid signal types"""
        return SignalClassifier.SIGNAL_TYPES

    @staticmethod
    def build_signal_counts_table_with_spares(summary_breakdown: Dict, spare_percentage: float = 0) -> Dict:
        """
        Build signal counts table with spares broken down by IO Type and unique combinations.
        
        Creates table with columns: IS-Red | IS-NonRed | NIS-Red | NIS-NonRed |
                                    IS-Red Spares | IS-NonRed Spares | NIS-Red Spares | NIS-NonRed Spares | Total
        
        Args:
            summary_breakdown: Dictionary from signal summary breakdown
                Example key: "AI|IS|Redundant" -> count
            spare_percentage: Percentage to allocate as spares (e.g., 20 for 20%)
        
        Returns:
            Dictionary with signal counts and spares per IO Type:
            {
                "AI": {
                    "IS-Red": 50,
                    "IS-NonRed": 50,
                    "NIS-Red": 20,
                    "NIS-NonRed": 30,
                    "IS-Red Spares": 10,
                    "IS-NonRed Spares": 10,
                    "NIS-Red Spares": 4,
                    "NIS-NonRed Spares": 6,
                    "Total": 180
                }
            }
        """
        signal_spares_table = {}
        
        for signal_type in ["AI", "DI", "DO", "AO"]:
            # Extract counts for each unique combination
            is_red_count = 0
            is_non_red_count = 0
            non_is_red_count = 0
            non_is_non_red_count = 0
            
            for key, count in summary_breakdown.items():
                parts = key.split("|")
                if parts[0] == signal_type:  # Match signal type
                    is_status = parts[1]
                    redundancy_status = parts[2]
                    
                    if is_status == "IS" and redundancy_status == "Redundant":
                        is_red_count += count
                    elif is_status == "IS" and redundancy_status == "Non-Redundant":
                        is_non_red_count += count
                    elif is_status == "Non-IS" and redundancy_status == "Redundant":
                        non_is_red_count += count
                    elif is_status == "Non-IS" and redundancy_status == "Non-Redundant":
                        non_is_non_red_count += count
            
            # Only add if IO Type has signals
            total_signals = is_red_count + is_non_red_count + non_is_red_count + non_is_non_red_count
            if total_signals == 0:
                continue
            
            # Calculate spares for each unique combination
            is_red_spares = round(is_red_count * (spare_percentage / 100)) if is_red_count > 0 else 0
            is_non_red_spares = round(is_non_red_count * (spare_percentage / 100)) if is_non_red_count > 0 else 0
            non_is_red_spares = round(non_is_red_count * (spare_percentage / 100)) if non_is_red_count > 0 else 0
            non_is_non_red_spares = round(non_is_non_red_count * (spare_percentage / 100)) if non_is_non_red_count > 0 else 0
            
            total_spares = is_red_spares + is_non_red_spares + non_is_red_spares + non_is_non_red_spares
            total_with_spares = total_signals + total_spares
            
            signal_spares_table[signal_type] = {
                "IS-Red": is_red_count,
                "IS-NonRed": is_non_red_count,
                "NIS-Red": non_is_red_count,
                "NIS-NonRed": non_is_non_red_count,
                "IS-Red Spares": is_red_spares,
                "IS-NonRed Spares": is_non_red_spares,
                "NIS-Red Spares": non_is_red_spares,
                "NIS-NonRed Spares": non_is_non_red_spares,
                "Total": total_with_spares
            }
        
        return signal_spares_table