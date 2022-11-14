"""Api declaration module."""
import asyncio
import csv
import json
import os
import os.path as osp
import re
import typing as tp

from fastapi import FastAPI
import aiohttp

from network_api.schemas import MobileNetworkData, MapBloc, MapGridBloc
from network_api.geo_utils import get_closest

app = FastAPI(title="mobile network coverage level")

@app.on_event("startup")
def load_network_data():
    """Loads mobile network coverage data map."""
    with open(
        osp.join(osp.dirname(__file__), "mobile_network_coverage.json"), 'r'
    ) as json_file:
        data = json.load(json_file)
    app.mnc_data = MobileNetworkData(**data)

CITY_PATTERN = re.compile(r"\d{4,6}.*$")

@app.get("/mobile-network-coverage/")
async def get_mobile_network_coverage(q: str) -> tp.Dict[
    tp.Literal['Orange', 'SFR', 'Freee', 'Bouygue'],
    tp.Dict[tp.Literal['2G', '3G', '4G'], bool]
]:
    """Returns network coverage for a query."""
    params = { "q": q, "limit" : 1 }
    result = None
    coords = None
    # Get coords from api-adresse.data.gouv.fr
    async with aiohttp.ClientSession(
        base_url="https://api-adresse.data.gouv.fr"
    ) as session:
        async with session.get("/search/", params = params) as resp:
            result = await resp.json()
        try:
            coords = result["features"][0]["geometry"]["coordinates"]
        except KeyError as err:
            city = CITY_PATTERN.match(q)
            if city is None:
                raise
            params["q"] = city[0]
            async with session.get("/search/", params = params) as resp:
                result = await resp.json()
            coords = result["features"][0]["geometry"]["coordinates"]
    # Search for coords in the data map
    c_long, c_lat = coords
    coverage = {}
    for provider, datas in app.mnc_data:
        cov = "Error"
        bloc = datas.map.search_leaf_bloc((c_long, c_lat))
        if bloc is None:
            cov = "Coordinate outside of geographic limit"
        elif (datapoints := bloc.get_outer_datapoints()):
            candidates = [datas.results[i] for i in datapoints]
            cov = get_closest(candidates, (c_long, c_lat))
        else:
            cov = "No coverage data in this area"
        coverage[provider] = cov
    return coverage

