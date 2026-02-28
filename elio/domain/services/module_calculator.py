"""Module calculator service."""
import math
from typing import Dict, List
from domain.models.module_instance import ModuleInstance


class ModuleCalculator:

    def create_instances(self, template, total_channels):

        count = math.ceil(total_channels / template.usable_channels)
        modules = []

        for i in range(count):
            modules.append(ModuleInstance(template, i+1))

        return modules

    @staticmethod
    def calculate_modules_for_signal_group(
        signal_count: int,
        is_redundant: bool,
        channels_per_module: int
    ) -> int:
        """
        Calculate modules required for a signal group considering redundancy.
        
        Args:
            signal_count: Number of signals in this group
            is_redundant: True if signals are redundant (requires 2 modules per signal)
            channels_per_module: Number of usable channels per module
        
        Returns:
            Number of modules required
            
        Logic:
            - Redundant: Each signal needs 2 modules → 2 * signal_count / channels_per_module (ceiling)
            - Non-Redundant: Signals share channels → signal_count / channels_per_module (ceiling)
        """
        if signal_count <= 0 or channels_per_module <= 0:
            return 0
        
        if is_redundant:
            # Redundant signals need 2 physical modules per signal group
            # So we need 2x the channels
            total_channels_needed = signal_count * 2
            modules_required = math.ceil(total_channels_needed / channels_per_module)
            print(f"[ModuleCalculator.calculate_modules_for_signal_group]")
            print(f"  REDUNDANT: {signal_count} signals × 2 = {total_channels_needed} channels needed")
            print(f"  Modules required: {modules_required} (with {channels_per_module} ch/module)\n")
        else:
            # Non-redundant signals can share channels
            modules_required = math.ceil(signal_count / channels_per_module)
            print(f"[ModuleCalculator.calculate_modules_for_signal_group]")
            print(f"  NON-REDUNDANT: {signal_count} signals = {signal_count} channels needed")
            print(f"  Modules required: {modules_required} (with {channels_per_module} ch/module)\n")
        
        return modules_required

    @staticmethod
    def calculate_module_allocation(signal_spares_table: Dict, available_modules: List[Dict]) -> Dict:
        """
        Calculate module requirements per IO Type by summing modules needed for each signal combination.
        
        Calculates modules separately for IS-Red, IS-NonRed, NIS-Red, NIS-NonRed combinations,
        then sums them to get total modules required (ensures isolation between signal categories).
        
        Args:
            signal_spares_table: Table from SignalClassifier.build_signal_counts_table_with_spares()
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
            available_modules: List of available modules from ModuleSelector
                [
                    {"IO_Type": "AI", "Module": "SY3K-FAIS", "Usable_Channels": 16},
                    ...
                ]
        
        Returns:
            Dictionary with module allocation per IO Type:
            {
                "AI": {
                    "Module": "SY3K-FAIS",
                    "IS-Red_Modules": 4,
                    "IS-NonRed_Modules": 4,
                    "NIS-Red_Modules": 2,
                    "NIS-NonRed_Modules": 2,
                    "Modules_Required": 12
                }
            }
        """
        modules_by_type = {}
        for module in available_modules:
            io_type = module.get("IO_Type")
            if io_type not in modules_by_type:
                modules_by_type[io_type] = module
        
        allocation = {}
        
        for io_type, signal_data in signal_spares_table.items():
            if io_type not in modules_by_type:
                allocation[io_type] = {
                    "Module": "N/A",
                    "Error": "No module found for IO Type"
                }
                continue
            
            module_info = modules_by_type[io_type]
            usable_channels = module_info.get("Usable_Channels", 0)
            
            if usable_channels <= 0:
                allocation[io_type] = {
                    "Module": module_info.get("Module", "Unknown"),
                    "Error": "Invalid usable channels"
                }
                continue
            
            # Calculate modules for each signal combination separately
            is_red_channels = signal_data.get("IS-Red", 0) + signal_data.get("IS-Red Spares", 0)
            is_nonred_channels = signal_data.get("IS-NonRed", 0) + signal_data.get("IS-NonRed Spares", 0)
            nis_red_channels = signal_data.get("NIS-Red", 0) + signal_data.get("NIS-Red Spares", 0)
            nis_nonred_channels = signal_data.get("NIS-NonRed", 0) + signal_data.get("NIS-NonRed Spares", 0)
            
            is_red_modules = math.ceil(is_red_channels / usable_channels) if is_red_channels > 0 else 0
            is_nonred_modules = math.ceil(is_nonred_channels / usable_channels) if is_nonred_channels > 0 else 0
            nis_red_modules = math.ceil(nis_red_channels / usable_channels) if nis_red_channels > 0 else 0
            nis_nonred_modules = math.ceil(nis_nonred_channels / usable_channels) if nis_nonred_channels > 0 else 0
            
            total_modules = is_red_modules + is_nonred_modules + nis_red_modules + nis_nonred_modules
            
            allocation[io_type] = {
                "Module": module_info.get("Module", "Unknown"),
                "IS-Red_Modules": is_red_modules,
                "IS-NonRed_Modules": is_nonred_modules,
                "NIS-Red_Modules": nis_red_modules,
                "NIS-NonRed_Modules": nis_nonred_modules,
                "Modules_Required": total_modules
            }
        
        return allocation

    @staticmethod
    def apply_redundancy_doubling(allocation: Dict) -> Dict:
        """
        Apply redundancy doubling for Red signal modules (redundant signals need 2x modules).
        
        Doubles Red_Modules count (for failover capability) while keeping NonRed_Modules as-is.
        
        Args:
            allocation: Dictionary from calculate_module_allocation()
                {
                    "AI": {
                        "Module": "SY3K-FAIS",
                        "IS-Red_Modules": 4,
                        "IS-NonRed_Modules": 4,
                        "NIS-Red_Modules": 2,
                        "NIS-NonRed_Modules": 2,
                        "Modules_Required": 12
                    }
                }
        
        Returns:
            Dictionary with redundancy applied:
            {
                "AI": {
                    "Module": "SY3K-FAIS",
                    "IS-Red_Modules": 8,         # doubled
                    "IS-NonRed_Modules": 4,      # unchanged
                    "NIS-Red_Modules": 4,        # doubled
                    "NIS-NonRed_Modules": 2,     # unchanged
                    "Modules_Required": 18       # new sum
                }
            }
        """
        redundancy_applied = {}
        
        for io_type, allocation_data in allocation.items():
            if "Error" in allocation_data:
                redundancy_applied[io_type] = allocation_data
                continue
            
            # Double Red modules for redundancy, keep NonRed modules as-is
            is_red_doubled = allocation_data.get("IS-Red_Modules", 0) * 2
            is_nonred_unchanged = allocation_data.get("IS-NonRed_Modules", 0)
            nis_red_doubled = allocation_data.get("NIS-Red_Modules", 0) * 2
            nis_nonred_unchanged = allocation_data.get("NIS-NonRed_Modules", 0)
            
            total_modules_with_redundancy = is_red_doubled + is_nonred_unchanged + nis_red_doubled + nis_nonred_unchanged
            
            redundancy_applied[io_type] = {
                "Module": allocation_data.get("Module", "Unknown"),
                "IS-Red_Modules": is_red_doubled,
                "IS-NonRed_Modules": is_nonred_unchanged,
                "NIS-Red_Modules": nis_red_doubled,
                "NIS-NonRed_Modules": nis_nonred_unchanged,
                "Modules_Required": total_modules_with_redundancy
            }
        
        return redundancy_applied

    @staticmethod
    def calculate_module_summary(allocation_before_redundancy: Dict, allocation_after_redundancy: Dict) -> Dict:
        """
        Calculate module summary with three key counts:
        - Single_Modules: Non-redundant modules only (IS-NonRed + NIS-NonRed)
        - Dual_Red_Modules: Redundant modules before doubling (IS-Red + NIS-Red)
        - Total_FIO_Modules: Total modules = Single_Modules + (Dual_Red_Modules × 2)
        
        Args:
            allocation_before_redundancy: Dictionary from calculate_module_allocation()
            allocation_after_redundancy: Dictionary from apply_redundancy_doubling()
        
        Returns:
            Dictionary with module summary:
            {
                "AI": {
                    "Module": "SY3K-FAIS",
                    "Single_Modules": 6,           # IS-NonRed(4) + NIS-NonRed(2)
                    "Dual_Red_Modules": 6,         # IS-Red(4) + NIS-Red(2) [before doubling]
                    "Total_FIO_Modules": 18        # 6 + (6 × 2)
                }
            }
        """
        summary = {}
        
        for io_type in allocation_before_redundancy.keys():
            before = allocation_before_redundancy.get(io_type, {})
            after = allocation_after_redundancy.get(io_type, {})
            
            if "Error" in before or "Error" in after:
                summary[io_type] = {
                    "Module": before.get("Module", "Unknown"),
                    "Error": "Cannot calculate summary"
                }
                continue
            
            # Single modules: Non-redundant only (before doubling)
            single_modules = before.get("IS-NonRed_Modules", 0) + before.get("NIS-NonRed_Modules", 0)
            
            # Dual Red modules: Redundant modules before doubling
            dual_red_modules = before.get("IS-Red_Modules", 0) + before.get("NIS-Red_Modules", 0)
            
            # Total FIO modules: Single + (Red × 2)
            total_fio_modules = single_modules + (dual_red_modules * 2)
            
            summary[io_type] = {
                "Module": before.get("Module", "Unknown"),
                "Single_Modules": single_modules,
                "Dual_Red_Modules": dual_red_modules,
                "Total_FIO_Modules": total_fio_modules
            }
        
        return summary
