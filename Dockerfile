# Copyright (c) 2018 Kinetica DB Inc.

# Kinetica Machine Learning
# Kinetica Machine Learning BlackBox Container SDK + Sample

FROM python:3.6
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils

# This is only for development debugging, will be removed when we go to PROD
RUN apt-get install -y git htop wget nano

RUN pip install gpudb zmq requests

RUN mkdir /opt/gpudb
RUN mkdir /opt/gpudb/kml
RUN mkdir /opt/gpudb/kml/api
WORKDIR "/opt/gpudb/kml/api"

ADD bb_module_default.py /opt/gpudb/kml/api/bb_module_default.py
ADD bb_runner.py /opt/gpudb/kml/api/bb_runner.py
ADD bb_runner.sh /opt/gpudb/kml/api/bb_runner.sh
ADD kinetica_black_box.py /opt/gpudb/kml/api/kinetica_black_box.py
ADD kmllogger.py /opt/gpudb/kml/api/kmllogger.py
ADD kmlutils.py /opt/gpudb/kml/api/kmlutils.py

RUN ["chmod", "+x",  "bb_runner.sh"]

ENTRYPOINT ["/opt/gpudb/kml/api/bb_runner.sh"]
