"""Module calculator service."""
import math
from domain.models.module_instance import ModuleInstance

class ModuleCalculator:

    def create_instances(self, template, total_channels):

        count = math.ceil(total_channels / template.usable_channels)
        modules = []

        for i in range(count):
            modules.append(ModuleInstance(template, i+1))

        return modules