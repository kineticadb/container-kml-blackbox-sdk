
# Kinetica Machine Learning BlackBox Container SDK

![Kinetica Logo](https://www.kinetica.com/wp-content/uploads/2018/08/kinetica_logo.svg "Kinetica Logo")

### Copyright (c) 2019 Kinetica DB Inc.
#### For support: support@kinetica.com


## Usage:

### STEP 1

- Clone and rename the repository `container-kml-blackbox-dep-base`

- Rename references to the container name in both `./build.sh` and
  `./publish.sh` to reflect the new name of your container


### STEP 2

- Derive a class from KineticaBlackBox. This base class is implemented in kinetica_black_box.py.

- Create a module file for the black box (eg. bb_module.py)

- In this file, import the base class:

```python
from kinetica_black_box import KineticaBlackBox
```

- Then, in this file, derive a new class from this:

```python
class MyBlackBox(KineticaBlackBox):
    def blackbox_function(self, inMap):
        # Call other functions in this file, in other files or insert blackbox code here
        # inMap and outMap are dicts() of the input and output parameters

        return outMap
```

### STEP 3. Call the new black box module from bb_runner.py

- In the main() routine of bb_runner.py, import the new black box class:

```python
from bb_module import MyBlackBox
```

- Then, also in the main routine, instantiate this class:

```python
bb = MyBlackBox(schema_inbound, schema_outbound,
                zmq_host, zmq_port, zmq_topic,
                db_table, db_host, db_port,
                db_user, db_pass)
```

- Then call the run method of this object:

```python
bb.run()
```

### STEP 4. Modify Dockerfile.

- ADD the new black box model file created above to the container image


### STEP 5. Build and push container

- Run ./build.sh then ./publish.sh to build the container according to the Docker file instructions and push to DockerHub or a private registry

- See blackbox pytest and API documentation for details on interacting with the deployed black box
