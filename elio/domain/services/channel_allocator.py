from domain.models.module_instance import ModuleInstance


class ChannelAllocator:

    @staticmethod
    def allocate(signals, template):
        modules = []

        for signal in signals:
            placed = False

            for m in modules:
                if m.has_capacity():
                    m.allocate(signal)
                    placed = True
                    break

            if not placed:
                new_module = ModuleInstance(
                    template_name=template.name,
                    channel_capacity=template.channel_capacity
                )
                new_module.allocate(signal)
                modules.append(new_module)

        return modules