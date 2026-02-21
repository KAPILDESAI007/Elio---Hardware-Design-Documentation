from domain.models.module_template import ModuleTemplate


class ConstraintLoader:

    @staticmethod
    def load_templates():
        return [
            ModuleTemplate(name="AI-16", signal_type="AI", channel_capacity=16),
            ModuleTemplate(name="DI-16", signal_type="DI", channel_capacity=16),
            ModuleTemplate(name="DO-16", signal_type="DO", channel_capacity=16),
            ModuleTemplate(name="AO-8", signal_type="AO", channel_capacity=8),
        ]