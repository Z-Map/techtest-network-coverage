"""Script to convert provided csv data to usable data."""
import csv
import json
from math import inf
import os.path as osp
import typing as tp
from copy import deepcopy
import warnings
warnings.filterwarnings('ignore')

import pyproj
import tqdm

from network_api.schemas import DataPoint, MapBloc

PROVIDER_MAPPING = {
    "20801" : "Orange",
    "20810" : "SFR",
    "20815" : "Free",
    "20820" : "Bouygue"
}

# Provided conversion function
def lamber93_to_gps(x, y):
	lambert = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs')
	wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
	longitude, latitude = pyproj.transform(lambert, wgs84, x, y)
	return longitude, latitude

def load_csv():
    loaded = 0
    metadata = {
        "long": { "min": inf, "max": -inf },
        "lat": { "min": inf, "max": -inf },
        "num": 0
    }
    results = {
        k:{"metadata": deepcopy(metadata), "results": []}
        for k in PROVIDER_MAPPING.values()
    }
    with open(osp.join(osp.dirname(__file__), "mobile_network_data_original.csv"), 'r', newline='') as datafile:
        reader = csv.reader(datafile, delimiter=';')
        for row in tqdm.tqdm(reader):
            if row[0] == 'Operateur':
                continue
            res = results[PROVIDER_MAPPING[row[0]]]
            coords = lamber93_to_gps(row[1], row[2])
            res["results"].append({
                "coords": {
                    "long": coords[0],
                    "lat": coords[1]
                },
                "2G": bool(int(row[3])),
                "3G": bool(int(row[4])),
                "4G": bool(int(row[5]))
            })
            for dim, i in (("long", 0), ("lat", 1)):
                res["metadata"][dim]["min"] = min(
                    res["metadata"][dim]["min"], coords[i])
                res["metadata"][dim]["max"] = max(
                    res["metadata"][dim]["max"], coords[i])
            res["metadata"]["num"] += 1
            loaded += 1
    print("Loaded", loaded)
    return results

def process_csv():
    # Cache load_csv as it takes a long time to run
    try:
        with open(
            osp.join(osp.dirname(__file__), "cached_data.json"
        ), 'r') as json_cache:
            results = json.load(json_cache)
    except OSError:
        results = load_csv()
        with open(
            osp.join(osp.dirname(__file__), "cached_data.json"
        ), 'w') as json_cache:
            json.dump(results, json_cache)
        print("Cache saved !")
    # Loop through providers
    for values in tqdm.tqdm(results.values()):
        # Sort the list based on longitude
        sorted_lst = sorted(
            values['results'],
            key=lambda item: item["coords"]["long"]
        )

        # Create a "voxel" map to quicly locate network record of network
        # coverage near specific coordinates 
        datanum = len(sorted_lst)
        datamap = MapBloc.auto_tile(
            values['metadata']['long']['min'] - 0.0001,
            values['metadata']['long']['max'],
            values['metadata']['lat']['min'] - 0.0001,
            values['metadata']['lat']['max'],
            set(range(datanum)),
            [ DataPoint(**dpoint) for dpoint in sorted_lst],
            max_inner = 50,
            max_outer = 150,
            min_set = 10,
            ignore_inner_bound_calc=1,
            ignore_outer_bound_calc=2
        )

        # Update values in provider's data
        values['results'] = sorted_lst
        values["map"] = json.loads(datamap.json())
    # Save results in a json file
    with open("mobile_network_coverage.json", "w") as json_file:
        json.dump(results, json_file)
    return {k: len(v["results"]) for k,v in results.items()}

if __name__ == "__main__":
    print(process_csv())