class CapacityValidator:

    @staticmethod
    def validate(modules):
        for m in modules:
            if len(m.signals) > m.channel_capacity:
                raise Exception("Module overfilled")