"""Geographic utility function."""
import typing as tp
import datetime
import math

from pydantic import BaseModel, Field

from network_api.schemas import DataPoint
from network_api.geo_math import Bound


def get_closest(candidates: tp.List[DataPoint], coords: tp.Tuple[float, float]):
	"""Returns the closest datapoint."""
	selected = None
	dist = math.inf
	for el in candidates:
		c_dist = math.dist(coords, el.coords.to_tuple())
		if c_dist < dist:
			selected = el
			dist = c_dist
	return {"2G": selected.has_2G, "3G": selected.has_3G, "4G": selected.has_4G}