from copy import deepcopy


class RedundancyHandler:

    @staticmethod
    def apply(modules):
        redundant_modules = []

        for m in modules:
            redundant_modules.append(m)
            backup = deepcopy(m)
            redundant_modules.append(backup)

        return redundant_modules