"""Contains pydantic schemas used by the api."""
import typing as tp
import datetime

from math import inf
from pydantic import BaseModel, Field

from network_api.geo_math import Bound

class Coords(BaseModel):
    """GPS Coordinates."""
    longitude: float = Field(default=0.0, alias="long")
    latitude: float = Field(default=0.0, alias="lat")

    def to_tuple(self):
        return (self.longitude, self.latitude)

class DataPoint(BaseModel):
    """Data point indicating coverage space at a specific location."""
    coords: Coords
    has_2G: bool = Field(alias="2G")
    has_3G: bool = Field(alias="3G")
    has_4G: bool = Field(alias="4G")

class MapBlocDim(BaseModel):
    """Dimension info for MapBloc schema."""
    o_min: float = -1.5
    o_max: float = 2.5
    i_min: float = 0.0
    i_max: float = 1.0
    mid: float = 0.5

    def __add__(self, other: int | float):
        return MapBlocDim(
            o_min = self.o_min + other,
            o_max = self.o_max + other,
            i_min = self.i_min + other,
            i_max = self.i_max + other,
            mid = self.mid + other
        )

    def __iadd__(self, other: int | float):
        self.o_min += other,
        self.o_max += other,
        self.i_min += other,
        self.i_max += other,
        self.mid += other
        return self

    def __sub__(self, other: int | float):
        return MapBlocDim(
            o_min = self.o_min - other,
            o_max = self.o_max - other,
            i_min = self.i_min - other,
            i_max = self.i_max - other,
            mid = self.mid - other
        )

    def __isub__(self, other: int | float):
        self.o_min -= other,
        self.o_max -= other,
        self.i_min -= other,
        self.i_max -= other,
        self.mid -= other
        return self

    def __mul__(self, other: int | float):
        offset = self.i_min
        return MapBlocDim(
            o_min = (self.o_min - offset) * other + offset,
            o_max = (self.o_max - offset) * other + offset,
            i_min = offset,
            i_max = (self.i_max - offset) * other + offset,
            mid = (self.mid - offset) * other + offset
        )

    def __imul__(self, other: int | float):
        offset = self.i_min
        self.o_min = (self.o_min - offset) * other + offset,
        self.o_max = (self.o_max - offset) * other + offset,
        self.i_max = (self.i_max - offset) * other + offset,
        self.mid = (self.mid - offset) * other + offset
        return self

    def __truediv__(self, other: int | float):
        offset = self.i_min
        return MapBlocDim(
            o_min = (self.o_min - offset) / other + offset,
            o_max = (self.o_min - offset) / other + offset,
            i_min = offset,
            i_max = (self.o_min - offset) / other + offset,
            mid = (self.mid - offset) / other + offset
        )

    def __itruediv__(self, other: int | float):
        offset = self.i_min
        self.o_min = (self.o_min - offset) / other + offset,
        self.o_max = (self.o_min - offset) / other + offset,
        self.i_max = (self.o_min - offset) / other + offset,
        self.mid = (self.mid - offset) / other + offset
        return self

    @classmethod
    def from_min_max(cls, dmin: float, dmax: float):
        """Create a new instance based on a min and max value pair."""
        size = dmax - dmin
        return (cls() * size) + dmin

    def __contains__(self, key: float):
        return (key >= self.o_min and key <= self.o_max)

class MapBloc(BaseModel):
    """2D square bloc which can contains either 4 sub bloc or a set of
       datapoint."""
    x: MapBlocDim
    y: MapBlocDim

    outer_set: tp.Set[int] = set()
    content: 'MapGridBloc' | tp.Set[int] | None = None

    def outer_bound(self):
        """Create a bound object corresponding to outer boundary."""
        return Bound(self.x.o_min, self.y.o_min, self.x.o_max, self.y.o_max)

    def inner_bound(self):
        """Create a bound object corresponding to inner boundary."""
        return Bound(self.x.i_min, self.y.i_min, self.x.i_max, self.y.i_max)

    def get_inner_datapoints(self) -> tp.Set[int]:
        """Returns inner datapoints indices as a set."""
        if isinstance(self.content, MapGridBloc):
            return self.content.get_inner_datapoints()
        elif self.content is None:
            return set()
        return self.content

    def get_outer_datapoints(self) -> tp.Set[int]:
        """Returns inner and outer datapoints indices as a set."""
        return self.outer_set | self.get_inner_datapoints()

    def search_leaf_bloc(
        self, coords: tp.Tuple[float, float]
    ) -> tp.Union['MapBloc', None]:
        """Search the leaf bloc corresponding to a specific location."""
        if coords not in self.inner_bound():
            return None
        if isinstance(self.content, MapGridBloc):
            if coords[0] > self.x.mid:
                if coords[1] > self.y.mid:
                    return self.content.bottomright.search_leaf_bloc(coords)
                else:
                    return self.content.topright.search_leaf_bloc(coords)
            else:
                if coords[1] > self.y.mid:
                    return self.content.bottomleft.search_leaf_bloc(coords)
                else:
                    return self.content.topleft.search_leaf_bloc(coords)
        return self

    @classmethod
    def auto_tile(cls,
        xmin: float, xmax: float,
        ymin: float, ymax: float, 
        index_set: tp.Set[int],
        datapoints: tp.List[DataPoint],
        max_inner: int = 6,
        max_outer: int = 20,
        min_set: int = 3,
        ignore_inner_bound_calc: int = 0,
        ignore_outer_bound_calc: int = 0
    ):
        """Create a full grid of blocs."""
        top_level = MapBloc(
            x = MapBlocDim.from_min_max(xmin, xmax),
            y = MapBlocDim.from_min_max(ymin, ymax),
        )
        inner_set = set()
        outer_set = index_set
        force_divide = False
        if ignore_inner_bound_calc > 0:
            ignore_inner_bound_calc -= 1
            force_divide = True
        else:
            bound = top_level.inner_bound()
            inner_set = set(
                i for i in index_set
                if datapoints[i].coords.to_tuple() in bound
            )
            outer_set = index_set - inner_set
        if ignore_outer_bound_calc > 0:
            ignore_outer_bound_calc -= 1
            force_divide = True
        else:
            bound = top_level.outer_bound()
            outer_set = set(
                i for i in outer_set
                if datapoints[i].coords.to_tuple() in bound
            )
        index_set = outer_set | inner_set
        if (len(inner_set) <= max_inner
            and len(outer_set) <= max_outer
            and not force_divide
        ) or len(index_set) <= min_set:
            top_level.outer_set = outer_set
            top_level.content = inner_set if len(inner_set) else None
        else:
            top_level.content = MapGridBloc(
                topleft = cls.auto_tile(
                    top_level.x.i_min, top_level.x.mid,
                    top_level.y.i_min, top_level.y.mid,
                    outer_set | inner_set, datapoints,
                    max_inner=max_inner, max_outer=max_outer,
                    ignore_inner_bound_calc=ignore_inner_bound_calc,
                    ignore_outer_bound_calc=ignore_outer_bound_calc
                ),
                topright = cls.auto_tile(
                    top_level.x.mid, top_level.x.i_max,
                    top_level.y.i_min, top_level.y.mid,
                    outer_set | inner_set, datapoints,
                    max_inner=max_inner, max_outer=max_outer,
                    ignore_inner_bound_calc=ignore_inner_bound_calc,
                    ignore_outer_bound_calc=ignore_outer_bound_calc
                ),
                bottomleft = cls.auto_tile(
                    top_level.x.i_min, top_level.x.mid,
                    top_level.y.mid, top_level.y.i_max,
                    outer_set | inner_set, datapoints,
                    max_inner=max_inner, max_outer=max_outer,
                    ignore_inner_bound_calc=ignore_inner_bound_calc,
                    ignore_outer_bound_calc=ignore_outer_bound_calc
                ),
                bottomright = cls.auto_tile(
                    top_level.x.mid, top_level.x.i_max,
                    top_level.y.mid, top_level.y.i_max,
                    outer_set | inner_set, datapoints,
                    max_inner=max_inner, max_outer=max_outer,
                    ignore_inner_bound_calc=ignore_inner_bound_calc,
                    ignore_outer_bound_calc=ignore_outer_bound_calc
                )
            )
            top_level.outer_set = index_set - top_level.get_outer_datapoints()
        return top_level

class MapGridBloc(BaseModel):
    """Internal subgrid needed as content of MapBloc."""
    topleft: MapBloc
    topright: MapBloc
    bottomleft: MapBloc
    bottomright: MapBloc

    def get_inner_datapoints(
        self, box_pos: int | tp.List[int] = [0, 1, 2, 3]
    ) -> tp.Set[int]:
        refs = (self.topleft, self.topright, self.bottomleft, self.bottomright)
        ret = set()
        for i in box_pos:
            ret = ret | refs[i].get_inner_datapoints()
        return ret

    def get_outer_datapoints(
        self, box_pos: int | tp.List[int] = [0, 1, 2, 3]
    ) -> tp.Set[int]:
        refs = (self.topleft, self.topright, self.bottomleft, self.bottomright)
        ret = set()
        for i in box_pos:
            ret = ret | refs[i].get_outer_datapoints()
        return ret

MapBloc.update_forward_refs()

class MinMaxPair(BaseModel):
    """Pair of values with a min and max."""
    minimal: float = Field(default=-inf, alias="min")
    maximal: float = Field(default=inf, alias="max")

class ProviderMetadata(BaseModel):
    """Provider metadata structure."""
    longitude: MinMaxPair = Field(alias="long")
    latitude: MinMaxPair = Field(alias="lat")
    num: int = 0

class ProviderData(BaseModel):
    """Provider main structure."""
    metadata: ProviderMetadata
    results: tp.List[DataPoint]
    map: MapBloc

class MobileNetworkData(BaseModel):
    """Mobile coverage data"""
    Orange: ProviderData
    SFR: ProviderData
    Free: ProviderData
    Bouygue: ProviderData

