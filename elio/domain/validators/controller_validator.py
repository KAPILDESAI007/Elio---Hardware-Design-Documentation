from settings import MAX_NODES_PER_CONTROLLER


class ControllerValidator:

    @staticmethod
    def validate(nodes):
        if len(nodes) > MAX_NODES_PER_CONTROLLER:
            raise Exception("Controller node limit exceeded")