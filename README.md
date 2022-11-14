# Mobile Network Coverage

Technical test, the goal is to get the network coverage at a specific address
sent as a url query.

Based on data from https://www.data.gouv.fr/s/resources/monreseaumobile/20180228-174515/2018_01_Sites_mobiles_2G_3G_4G_France_metropolitaine_L93.csv saved here in  `script/mobile_network_data_original.csv`

## Install & Run

To install the project you need poetry : 
```zsh
poetry install
```

After insrtallation is successful, use this command to run it :
```zsh
poetry run uvicorn network_api.api:app
```

## Coverage Data Map Generation

The service use preprocessed data to found the coverage level for a query. The preprocess is done by the script `convert_data.py` which generate a json from the input csv.

The script does the following :
 - Transform Lambert93 coordinates to standard GPS coordinates.
 - Sort datapoint into list for each provider
 - Build a 2d adaptative grid to optimize runtime operation

The adaptive grid works by spliting every area in four area recursively until each induvidual area only contains a certain amount of datapoint. Each area have a "outer limit" around it to make sure that any point inside the area can find the closest Datapoint.

To regenerate the file use this command :
```zsh
poetry run python script/convert_data.py
```
