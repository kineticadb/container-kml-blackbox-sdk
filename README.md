# Kinetica Blackbox Software Development Kit (SDK)

---

## Overview

The Blackbox SDK provides a container-based interface to user provided models for use
with the Kinetica database. Model code may be a computational analyitc of any type
including, but not limited to, machine learning algorithms. Container management and
both batch and continuous deployment invocations are accessible with SQL commands
in Kinetica Workbench.

> NOTE: While the KML api remains supported, an earlier stand-alone UI known as AAW 
has been deprecated in favor of SQL bindings (ml-sql) and integration into the new 
Workbench user interface for Kinetica.

## Prerequisites

* [Docker](https://www.docker.com/get-started)
* Container registry such as Docker Hub, AWS ECR, DOCR etc
* Kinetica 7.1 AWS or Azure marketplace (PaaS) deployment or a On-Prem KAgent installation
of Kinetica 7.1 with a user connected Kubernetes cluster
 
## Container structure

Models are represented as functions within a module file. Though not required, you can
have multiple function within multiple module files all in a single container as a method
of consolidating all model assets.

The SDK is written in Python 3 and this is the only officially supported language for
model code. However, an advanced user will note that it is theoretically possible to run
other code and binaries inside the container and call out to it via the python module
wrapper.

Any required libraries and static assets (including model binaries (pickle, onyx etc) and
weights files) are added to the container at build time via the Dockerfile.

This guide exists on-line at: [Kinetica Blackbox Software Development Kit (SDK) Guide](http://www.kinetica.com/docs/7.0/aaw/blackbox_sdk.html)

See [Kinetica Documentation](http://www.kinetica.com/docs/7.1/index.html) for general product usage

-----

##  Preparing the model files

1. Clone the Blackbox SDK github project

```commandline
git clone https://github.com/kineticadb/container-kml-blackbox-sdk.git
cd container-kml-blackbox-sdk
```
Overview of SDK files and their use:

| Filename               | Description                                                                                    |
|------------------------|------------------------------------------------------------------------------------------------|
| `sdk/bb_runner.py`     | * Kinetica database interface module.                                                          |
| `bb_runner.sh`         | * Container entrypoint. Starts sdk/bb_runner.py.                                               |
| `Dockerfile`           | Image build file. Add modules and assets here                                                  |
| `bb_module_default.py` | Sample model module with example functions. Edit this file or create you're own.               |
| `requirements.txt`     | Required Python libraries for your model. Packages `gpudb`, `zmq` and `requests` are required. |
| `spec.json`            | Required introspection manifest which makes information about your models available to the DB. |                                                          

`*` Editing these files in not recommended or supported

2. Add model code

Update `bb_module_default.py` with the desired model code. The model can contain as many functions as desired or 
call as many other modules as desired, but the default function definition **must** take a dictionary in (`inputs`)
and return a dictionary (`outputs`). Optionally you can copy and rename this file, remove all the function definitions
and add your own.

3. Update model manifest

The file `spec.json` provides the name of the entry function for your model and the module file in which it is located.
It also details the schema for both the input and output variable used buy each model and any in-container environment
variables they may require. This file is read by the database when introspecting and configuring a model and **must not
be renamed**. All model descriptions are included in this single manifest; there will be only one `spec.json` file.

It is recommended that `spec.json` be copied to another file, eg. 
```commandline
cp spec.json original_spec.json
```
then edit 
`spec.json` using the original as a reference. The manifest added to the container in the Dockerfile and thus used by 
your models must be named `spec.json`. Or use the trivial example found at the end of this README.

The *main block* of the manifest file contains the following required key:value pairs:

| Key         | Type   | Description                                                             |
|-------------|--------|-------------------------------------------------------------------------|
| `name`      | string | A name for the manifest (for user reference only).                      |
| `desc`      | string | A description of the manifest (for user reference only).                |
| `src_uri`   | string | The URI of the image as <registry>/<repo>/<image>:<tag>                 |
| `type`      | string | Problem type for the models. Always "BLACKBOX".                         |
| `functions` | array  | A list containing nested objects (see below) for each model function.   |

`name` and `desc` are required but only serve to document this file so they can contain any text. `type` is 
reserved for future functionality, in this case it must always be "BLACKBOX"

The *functions block* of the manifest can contain references to as many model entry functions as
you have in one or many module files. The structure is:

| Key                  | Type   | Description                                                           |
|----------------------|--------|-----------------------------------------------------------------------|
| `name`               | string | A name for the model function (for user reference only).              |
| `desc`               | string | A description of the model function (for user reference only).        |
| `bb_module`          | string | The module file containing the function (excluding the .py extension) |
| `bb_function`        | string | The name of the entry function for the model in the module above.     |
| `input_record_type`  | array  | Schema for the input variables as list of objects (see below).        |
| `output_record_type` | array  | Schema for the output variables as list of objects (see below).       |
| `env_vars`           | array  | A list of K:V pairs for container environment variables.              |
| `compute-support`    | array  | A list of supported compute requirements. "CPU" or "GPU".             |

`name` and `desc` are required but only serve to document the function in this file so they can contain any 
text. `env_vars` must also be added in the Dockerfile if any are required for the model. They are included
here for documentation purposes. `compute-support` may contain only "CPU" or "GPU". The latter requires a
GPGPU equipped Kubernetes cluster with the NVIDIA driver installed.

The *input_record_type* and *output_record_type* lists contain K:V blocks of the following format. One for
each of the model input and output variables in the appropriate section. The input table (specified on deployment)
**must** contain variables with the exact name and type specified here. The output table is automatically
generated based on a table name provided during deployment. The schema of the output table is generate using
the output_record_type specified below in addition to other columns containing the input variables (echoed for 
auditing purposes), success flags, UUID's and any model failure logs.

| Key         | Type   | Description                                                           |
|-------------|--------|-----------------------------------------------------------------------|
| `col_name`  | string | A name for the model function (for user reference only).              |
| `col_type`  | string | A description of the model function (for user reference only).        |
| `bb_module` | string | The module file containing the function (excluding the .py extension) |

>NOTE: An output table name is specified during deployment but this table is generated by the system and 
**must not** be pre-created.

The `spec.json` file can be validated with Python:
```commandline
python -mjson.tool spec.json > /dev/null
```
This will only generate an error is there is a JSON syntax issue

## Build configuration

4. Update the Python requirements file

If you have imported packages beyond the Python standard library in your module file they must also be added to the
`requirements.txt` file. Example:
```
scikit-learn==1.2.2
```
Not specifying a version will of course pull latest during the image build with potentially
unintended consequences. There will be only one requirements file for all model functions and modules (if you are
using more than one).

5. Update the Dockerfile

Edit the `Dockerfile` to ADD modules files other than `bb_module_default.py` and `bb_module_temperture.py` if you 
have create a new one in step 1 above. Example:
```
ADD <my_module_file.py> ./
```
The two included sample modules (default and temperature) are not required if you have created a new one.
If you are loading additional resources in your module such as pickled model binaries, weights files for ML models, 
lookup tables etc. they must also be ADDed in the Dockerfile so that they are included in the image on build. Example:
```
ADD <my_sklearn_model.pkl> ./
```
No action is needed for the `spec.json` models manifest or the `requirements.txt` package index. Even though you will 
have edited them in steps 3 and 4 respectivly above they are already included in the Dockerfile and must not be 
renamed or the system will not be able to load them.

>NOTE: Only edit the [user editable] sections of the Dockerfile

## Build and push image

6. Use docker to build the image locally and then push to your desired registry

```commandline
docker build -f Dockerfile -t <registry>/<repo-name>/<image-name>:<tag-name> .
```

7. Push image to your desired registry
```commandline
docker push <registry><repo-name>/<image-name>:<tag-name>
```

## Deploying the model via Kinetica Workbench

Deploying a model in Kinetica involves creating a container registry, importing a model from that 
registry (introspection) and then launching the containerized model in either batch or continuous 
(streaming) modes. SQL bindings are provided for these actions and are described in detain in the 
main [documentation](https://docs.kinetica.com/7.1/sql/ml/).

## Example JSON manifest (spec.json)
```json
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
```

