"""Math geometric utils."""
import math
import typing as tp

class Bound:
    """Boundaries utility class"""

    def __init__(self, x: float, y: float, x_end: float, y_end: float):
        self.x = x
        self.y = y
        self.x_end = x_end 
        self.w = x_end - x
        self.y_end = y_end
        self.h = y_end - y

    def __contains__(self, key: tp.Tuple[float, float]):
        return (
            (key[0] > self.x and key[0] <= self.x_end)
            and (key[1] > self.y and key[1] <= self.y_end)
        )