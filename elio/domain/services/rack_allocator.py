from settings import SLOTS_PER_NODE
from domain.models.node import Node


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