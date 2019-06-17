# Copyright (c) 2019 Kinetica DB Inc.

# Kinetica Machine Learning
# Kinetica Machine Learning BlackBox Container SDK + Sample

FROM python:3.6
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils

# This is only for debugging
# This can safely be removed in PROD settings, if desired
RUN apt-get install -y git htop wget nano

RUN pip install gpudb==7.0.3.0 zmq requests

RUN mkdir /opt/gpudb
RUN mkdir /opt/gpudb/kml
RUN mkdir /opt/gpudb/kml/bbx
WORKDIR "/opt/gpudb/kml/bbx"

ADD bb_module_default.py /opt/gpudb/kml/bbx/bb_module_default.py
ADD bb_runner.py /opt/gpudb/kml/bbx/bb_runner.py
ADD bb_runner.sh /opt/gpudb/kml/bbx/bb_runner.sh
ADD kinetica_black_box.py /opt/gpudb/kml/bbx/kinetica_black_box.py
ADD kmllogger.py /opt/gpudb/kml/bbx/kmllogger.py
ADD kmlutils.py /opt/gpudb/kml/bbx/kmlutils.py

RUN ["chmod", "+x",  "bb_runner.sh"]

ENTRYPOINT ["/opt/gpudb/kml/bbx/bb_runner.sh"]
