# Kinetica Blackbox Software Development Kit (SDK)

This project contains the **7.0.x.y** version of the **Kinetica Blackbox Software Development Kit** for integration of *Kinetica* with custom blackbox models.

This guide exists on-line at: [Kinetica Blackbox Software Development Kit (SDK) Guide](http://www.kinetica.com/docs/7.0/aaw/blackbox_sdk.html)

More information can be found at: [Kinetica Documentation](http://www.kinetica.com/docs/7.0/index.html)

-----

# Kinetica Blackbox SDK Guide

The Kinetica Blackbox SDK assists users in creating blackbox models to wrap existing code/functionality and make it deployable within the Kinetica system. The Active Analytics Workbench (AAW) currently can only import blackbox models that have been containerized and implement the BlackBox SDK. Users provide the Python module scripts, modify some SDK files, and the SDK will build a Docker Container from the files and publish it to a given Docker Registry (private or public).

For help with containerizing models, the Kinetica Blackbox Wizard is available via the [Model + Analytics portion](https://www.kinetica.com/docs/aaw/models_analytics.html#bb-model-import) of the AAW User Interface (UI).

## Prerequisites

* [Docker](https://www.docker.com/get-started)
* Docker [Hub](https://hub.docker.com/) / Docker Registry

## Download and Configuration

1. Clone the project and change directory into the folder:

        git clone https://github.com/kineticadb/container-kml-blackbox-sdk.git
        cd container-kml-blackbox-sdk

2. Get a list of tags for the repository:

        git tag -l

3. Check out the desired tagged version of the repository

        git checkout tags/<tag_name>

    **IMPORTANT:** The SDK version should be less than or equal to the current version of the database that the blackbox model will be running against. The latest version compatible is preferred. For example, if Kinetica is at version 7.0.3.0, the SDK tag version should be less than or equal to 7.0.3.0.

## Setup

The repository contains all the files needed to build and publish a blackbox model Docker container compatible with AAW. The important files and their function:

**WARNING:** It's highly recommended the ``sdk/*`` and ``bb_runner.sh`` files are not modified!

| Filename                    | Description                                                                                                                                                           |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `sdk/bb_runner.py`          | Python script called from the Docker container entrypoint script. Contains the code necessary for the module(s) to interface with the `kinetica_black_box.py` script. |
| `sdk/kinetica_black_box.py` | Python script called from `bb_runner.py`. Contains the code necessary for the blackbox module(s) to interface with the database.                                      |
| `Dockerfile`                | File containing all the instructions for Docker to build the model image properly.                                                                                    |
| `bb_module_default.py`      | Python script containing model code. The default code is a template for you to reuse and/or replace.                                                                  |
| `bb_runner.sh`              | Entrypoint for the Docker container; this script will be run initially when AAW pulls the container for execution.                                                    |
| `release.sh`                | Utility script for building and publishing the model to a Docker Hub or Docker Registry.                                                                              |
| `requirements.txt`          | Text file that stores the required python libraries for the model. Default libraries (`gpudb`, `zmq`, `requests`) must be left intact.                                |

To setup the repository for publishing your model:

1. Update `bb_module_default.py` with the desired model code. The model can contain as many methods as desired or call as many other modules as desired, but the default method **must** take a dictionary in (`inMap`) and return a dictionary (`outMap`):

        import math

        def predict_taxi_fare(inMap=None):

            # method code ...

            # Calculate fare amount from trip distance
            fare_amount = (dist * 3.9)

            outMap = {'fare_amount': fare_amount}

            return outMap

1. Optionally, update the name of `bb_module_default.py`. If the module name is updated, it will need to be referenced appropriately when deploying the model via the AAW UI or the AAW REST API. See the *Usage* section for more information.

1. Open the `Dockerfile` in an editor and include any required installations that are not easily installable with `pip`:

        RUN apt-get install -y git wget

1. Add all module files:

        ADD <module file.py> ./

   **IMPORTANT:** By default, the `Dockerfile` includes a reference to `bb_module_default.py`. This reference **must** be updated if the file name was changed earlier.

1. Open `requirements.txt` in an editor and include any additional required python libraries::

        numpy==1.16.3
        tensorflow

   **IMPORTANT:** The default `gpudb`, `zmq`, and `requests` packages inside `requirements.txt` **must** be left in the file.

1. Open `release.sh` in a text editor and update the repository, image,  and tag for both the `build` and `push` statements:

        docker build -f Dockerfile -t <repo-name>/<image-name>:<tag-name> .
        docker push <repo-name>/<image-name>:<tag-name>

   **TIP:** The Docker repository will be created if it doesn't exist.

## Usage

### Publishing the Model

1. Login into your Docker Hub or Docker Registry:

        # Docker Hub
        docker login

        # Docker Registry
        docker login <hostname>:<port>

2. Run the `release.sh` script to build a Docker image of the model and publish it to the provided Docker Hub or Docker Registry:

        ./release.sh

### Importing the Model

After publishing the model, it can be imported into AAW using two methods:

* REST API (via `cURL`)
* AAW User Interface (UI)

#### REST API

If using the REST API, a model is defined using JSON. The `cURL` command line tool can be used to send a JSON string or file to AAW. To import a blackbox model into AAW using ``cURL`` and the REST API: 

1. Define the model. *Kinetica* recommends placing the model definition inside a local JSON file.
1. Post the JSON to the `/model/blackbox/instance/create` endpoint of the AAW REST API:

        # Using a JSON file
        curl -X POST -H "Content-Type: application/json" -d @<model_file>.json http://<kinetica-host>:9187/kml/model/blackbox/instance/create

        # Using a JSON string
        curl -X POST -H "Content-Type: application/json" -d '{"model_inst_name": "<model_name>", ... }' http://<kinetica-host>:9187/kml/model/blackbox/instance/create

To aid in creating the necessary JSON, use the following endpoint and schema:

**Endpoint name**: ``/model/blackbox/instance/create``

**Input parameters**:

| Name | Type | Description |
|---------------------|---------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `model_inst_name` | string | Name of the model. |
| `model_inst_desc` | string | Optional description of the model. |
| `problem_type` | string | Problem type for the model. Always `BLACKBOX`. |
| `model_type` | string | Type for the model. Always `BLACKBOX`. |
| `input_record_type` | array of map(s) of strings to strings | An array containing a map for each input column. Requires two keys. Valid key name, type, and descriptions found below. |
| `model_config` | map of strings to various | A map containing model configuration information. Valid key name, type, and descriptions found below. |

Array `input_record_type` of map keys:

**IMPORTANT:** There will need to be as many maps (containing both name and type) as there are columns in the `inMap` variable inside the default blackbox module.

| Name | Type | Description |
|------------|--------|----------------------------|
| `col_name` | string | Name for the input column. |
| `col_type` | string | Type for the input column. |

Map `model_config` keys:

**IMPORTANT:** There will need to be as many maps (containing both name and type) in `output_record_type` as there are columns in the `outMap` variable inside the default blackbox module.

| Name | Type | Description |
|----------------------|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `db_user` | string | Username for database authentication. |
| `db_pass` | string | Password for database authentication. |
| `blackbox_module` | string | Module name for the blackbox model. |
| `blackbox_function` | string | Function name inside the blackbox module. |
| `container` | string | Docker URI for the container, e.g., `<repo_name>/<image_name>:<tag_name>` |
| `output_record_type` | string | An array containing a map for each output column. Similar to `input_record_type`, requires two keys: `col_name` -- a string value representing the name of the output column; `col_type` -- a string value representing the type of the output column. |

**Example JSON**:

The final JSON string should look similar to this:

    {
      "model_inst_name": "Taxi Fare Predictor",
      "model_inst_desc": "Blackbox model for on-demand deployments",
      "problem_type": "BLACKBOX",
      "model_type": "BLACKBOX",
      "input_record_type": [
        {
          "col_name": "pickup_longitude",
          "col_type": "float"
        },
        {
          "col_name": "pickup_latitude",
          "col_type": "float"
        },
        {
          "col_name": "dropoff_longitude",
          "col_type": "float"
        },
        {
          "col_name": "dropoff_latitude",
          "col_type": "float"
        }
      ],
      "model_config": {
        "db_user": "",
        "db_pass": "",
        "blackbox_module": "bb_module_default",
        "blackbox_function": "predict_taxi_fare",
        "container": "kinetica/kinetica-blackbox-quickstart:7.0.1",
        "output_record_type": [
          {
            "col_name": "fare_amount",
            "col_type": "double"
          }
        ]
      }
    }

#### AAW User Interface (UI)

The AAW UI offers a simpler WYSIWYG-style approach to importing a blackbox model. To import a blackbox model into the UI:

1. Navigate to the AAW UI (`http://<aaw-host>:8070`)
1. Click `Models + Analytics`.
1. Click `+ Add Model` then `Import Blackbox`.
1. Provide a `Model Name` and optional `Model Description`.
1. Input the Docker URI for the container, e.g., `<repo_name>/<image_name>:<tag_name>`
1. Input the `Module Name` and `Module Function`.
1. For `Input Columns`:

   1. Click `Add Input Column` to create input columns.
   1. Provide a `Column` name and `Type`.

1. For `Output Columns`:

   1. Click `Add Output Column` to create output columns.
   1. Provide a `Column` name and `Type`.

1. Click :guilabel:`Create`.

**Example UI**:

The final UI inputs should look similar to this:

![aaw ui new blackbox model filled](http://www.kinetica.com/docs/7.0/aaw/img/aaw_ui_new_bb_model_filled.png)
