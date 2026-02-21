class ModuleSelector:

    @staticmethod
    def select(signal_type, templates):
        for t in templates:
            if t.signal_type == signal_type:
                return t
        raise Exception(f"No template for {signal_type}")