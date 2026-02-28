from settings import SLOTS_PER_NODE
from domain.models.node import Node
import pandas as pd


class RackAllocator:

    @staticmethod
    def assign(modules):
        nodes = []
        current_node = Node(node_id=1)
        slot_counter = 1

        for module in modules:

            if slot_counter > SLOTS_PER_NODE:
                nodes.append(current_node)
                current_node = Node(node_id=len(nodes) + 1)
                slot_counter = 1

            module.slot_number = slot_counter
            module.node_id = current_node.node_id

            current_node.modules.append(module)
            slot_counter += 1

        nodes.append(current_node)
        return nodes

    @staticmethod
    def allocate_modules_to_rack(excel_path: str, module_summary: dict, available_modules: list) -> dict:
        """
        Allocate modules to rack slots based on Mounting_Rule sheet with pairing logic.
        
        Creates nodes dynamically as needed to fit all modules.
        
        Allocation Strategy:
        - Node=1: Replace IOM entries with module names (Single first, then Dual_Red pairs)
        - Node>=2: Use >=2 pattern (keep non-IOM as-is)
        
        Args:
            excel_path: Path to Yokogawa_SIS_Constraints_Model_v3.xlsx
            module_summary: Dictionary from ModuleCalculator.calculate_module_summary()
            available_modules: List of available modules
        
        Returns:
            Dictionary with all nodes and their module allocations
        """
        try:
            # Read Mounting_Rule sheet
            mounting_rules_df = pd.read_excel(excel_path, sheet_name="Mounting_Rule")
            
            # Create a mapping of IO_Type to Module name
            module_map = {}
            for module in available_modules:
                io_type = module.get("IO_Type")
                module_name = module.get("Module")
                if io_type and module_name:
                    module_map[io_type] = module_name
            
            # Create a working copy of module_summary to track allocation
            module_counts = {}
            total_modules_to_allocate = 0
            for io_type, summary in module_summary.items():
                if "Error" not in summary:
                    module_counts[io_type] = {
                        "module_name": module_map.get(io_type, io_type),
                        "single_remaining": summary.get("Single_Modules", 0),
                        "dual_red_remaining": summary.get("Dual_Red_Modules", 0)
                    }
                    # Use Total_FIO_Modules which already accounts for doubling
                    total_modules_to_allocate += summary.get("Total_FIO_Modules", 0)
            
            # Extract Node-1 template (IOM slots only)
            node1_iom_slots = []
            node1_other_slots = {}
            pattern_rules = {}
            
            for _, row in mounting_rules_df.iterrows():
                node_no = str(row.get("Node No", "")).strip()
                slot = row.get("Slot")
                item_type = row.get("Type")
                
                if pd.isna(slot):
                    continue
                
                slot_num = int(slot)
                slot_key = f"Slot-{slot_num}"
                
                if node_no == "1":
                    if str(item_type).upper() == "IOM":
                        node1_iom_slots.append((slot_num, slot_key))
                    else:
                        # Preserve non-IOM items in Node-1
                        node1_other_slots[slot_key] = item_type
                elif node_no == ">=2":
                    pattern_rules[slot_key] = item_type
            
            node1_iom_slots = sorted(node1_iom_slots)
            
            # Calculate nodes needed: Node-1 has IOM slots, subsequent nodes have fixed slots
            slots_per_node = 12  # Standard rack slots
            nodes_needed = max(1, -(-total_modules_to_allocate // slots_per_node))  # Ceiling division
            
            # Build all nodes
            rack_allocation = {}
            
            # Create all nodes with pattern
            for node_num in range(1, nodes_needed + 1):
                node_key = f"Node-{node_num}"
                rack_allocation[node_key] = {}
                
                # Initialize all 12 slots
                for slot_num in range(1, slots_per_node + 1):
                    slot_key = f"Slot-{slot_num}"
                    
                    if node_num == 1:
                        # For Node-1: apply node1_other_slots first (PSU, PDI, etc.)
                        # IOM slots will be empty, to be filled with modules
                        rack_allocation[node_key][slot_key] = node1_other_slots.get(slot_key, "")
                    else:
                        # For Node>=2: apply pattern
                        pattern_item = pattern_rules.get(slot_key, "")
                        # If pattern says "IOM", leave it empty for module allocation
                        # Otherwise keep the fixed item (PSU, PDI, etc.)
                        if str(pattern_item).upper() == "IOM":
                            rack_allocation[node_key][slot_key] = ""
                        else:
                            rack_allocation[node_key][slot_key] = pattern_item
            
            # Now allocate modules to Node-1 IOM slots with pairing logic
            slot_index = 0
            
            while slot_index < len(node1_iom_slots):
                slot_num, slot_key = node1_iom_slots[slot_index]
                
                # Calculate consecutive slots available
                consecutive_slots = 1
                if slot_index + 1 < len(node1_iom_slots):
                    next_slot_num = node1_iom_slots[slot_index + 1][0]
                    if next_slot_num == slot_num + 1:
                        consecutive_slots = 2
                
                slot_filled = False
                
                # First priority: Single modules (1 slot)
                if not slot_filled:
                    for io_type in module_counts:
                        if module_counts[io_type]["single_remaining"] > 0:
                            rack_allocation["Node-1"][slot_key] = module_counts[io_type]["module_name"]
                            module_counts[io_type]["single_remaining"] -= 1
                            slot_filled = True
                            slot_index += 1
                            break
                
                # Second priority: Dual_Red modules (2 consecutive slots)
                if not slot_filled and consecutive_slots >= 2:
                    for io_type in module_counts:
                        if module_counts[io_type]["dual_red_remaining"] > 0:
                            slot_num_2, slot_key_2 = node1_iom_slots[slot_index + 1]
                            rack_allocation["Node-1"][slot_key] = module_counts[io_type]["module_name"]
                            rack_allocation["Node-1"][slot_key_2] = module_counts[io_type]["module_name"]
                            module_counts[io_type]["dual_red_remaining"] -= 1
                            slot_filled = True
                            slot_index += 2
                            break
                
                # If not even 1 slot available for remaining modules (skip slot)
                if not slot_filled:
                    rack_allocation["Node-1"][slot_key] = ""
                    slot_index += 1
            
            # Allocate remaining modules to subsequent nodes
            for node_num in range(2, nodes_needed + 1):
                node_key = f"Node-{node_num}"
                
                # Find slots available in this node (empty slots from pattern application)
                available_slots = []
                for slot_num in range(1, slots_per_node + 1):
                    slot_key = f"Slot-{slot_num}"
                    if rack_allocation[node_key][slot_key] == "":
                        available_slots.append((slot_num, slot_key))
                
                available_slots = sorted(available_slots)
                slot_index = 0
                
                while slot_index < len(available_slots):
                    slot_num, slot_key = available_slots[slot_index]
                    
                    # Check consecutive availability
                    consecutive_slots = 1
                    if slot_index + 1 < len(available_slots):
                        next_slot_num = available_slots[slot_index + 1][0]
                        if next_slot_num == slot_num + 1:
                            consecutive_slots = 2
                    
                    slot_filled = False
                    
                    # Single modules first
                    if not slot_filled:
                        for io_type in module_counts:
                            if module_counts[io_type]["single_remaining"] > 0:
                                rack_allocation[node_key][slot_key] = module_counts[io_type]["module_name"]
                                module_counts[io_type]["single_remaining"] -= 1
                                slot_filled = True
                                slot_index += 1
                                break
                    
                    # Dual_Red modules
                    if not slot_filled and consecutive_slots >= 2:
                        for io_type in module_counts:
                            if module_counts[io_type]["dual_red_remaining"] > 0:
                                slot_num_2, slot_key_2 = available_slots[slot_index + 1]
                                rack_allocation[node_key][slot_key] = module_counts[io_type]["module_name"]
                                rack_allocation[node_key][slot_key_2] = module_counts[io_type]["module_name"]
                                module_counts[io_type]["dual_red_remaining"] -= 1
                                slot_filled = True
                                slot_index += 2
                                break
                    
                    if not slot_filled:
                        slot_index += 1
            
            return rack_allocation
        
        except Exception as e:
            return {
                "Error": f"Failed to allocate modules to rack: {str(e)}"
            }
