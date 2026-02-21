from collections import defaultdict
from settings import SPARE_PERCENT_DEFAULT
from infrastructure.constraint_loader import ConstraintLoader
from domain.services.spare_calculator import SpareCalculator
from domain.services.module_selector import ModuleSelector
from domain.services.channel_allocator import ChannelAllocator
from domain.services.rack_allocator import RackAllocator
from domain.validators.controller_validator import ControllerValidator
from domain.validators.capacity_validator import CapacityValidator


class Orchestrator:

    def __init__(self):
        self.templates = ConstraintLoader.load_templates()

    def run(self, signals, spare_percent=SPARE_PERCENT_DEFAULT):

        grouped = defaultdict(list)
        for s in signals:
            grouped[s.signal_type].append(s)

        all_modules = []

        for signal_type, group in grouped.items():

            template = ModuleSelector.select(signal_type, self.templates)

            total = SpareCalculator.apply(len(group), spare_percent)

            expanded = group.copy()
            while len(expanded) < total:
                expanded.append(group[-1])

            modules = ChannelAllocator.allocate(expanded, template)
            all_modules.extend(modules)

        CapacityValidator.validate(all_modules)

        nodes = RackAllocator.assign(all_modules)

        ControllerValidator.validate(nodes)

        return nodes