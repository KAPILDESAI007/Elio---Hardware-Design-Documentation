import math


class SpareCalculator:

    @staticmethod
    def apply(count, spare_percent):
        return math.ceil(count * (1 + spare_percent / 100))