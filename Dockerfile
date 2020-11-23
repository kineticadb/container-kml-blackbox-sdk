# Copyright (c) 2020 Kinetica DB Inc.
#
# Kinetica Machine Learning
# Kinetica Machine Learning BlackBox Container SDK + Trivial Samples
#
# for support, contact Saif Ahmed (support@kinetica.com)
#


# End users are welcome to use any python-3.6 base container of their choice
FROM kinetica/ctnr-kml-base-cpu:revision01

LABEL maintainer="support@kinetica.com"
LABEL Description="Kinetica Machine Learning BlackBox SDK and starter examples."
LABEL Author="Saif Ahmed; Julian Jenkins"

RUN mkdir -p /opt/gpudb/kml/bbx
RUN mkdir -p /opt/gpudb/kml/bbx/specs
WORKDIR "/opt/gpudb/kml/bbx"

# Install Required Libraries and Dependencies
ADD requirements.txt  ./
RUN pip install --upgrade pip
# ADD gpudb-api-python/gpudb-*-cp36-cp36m-manylinux1_x86_64.whl ./
# RUN pip install ./gpudb-*.whl
RUN pip install -r requirements.txt --no-cache-dir

# Add introspection assets
ADD *.json ./specs/

# Add Kinetica BlackBox SDK
ADD bb_runner.sh ./
ADD sdk ./sdk

ADD bb_module_default.py ./
ADD bb_module_temperature.py ./
ADD bb_module_tests.py ./
ADD bb_module_stress.py ./

ADD END_USER_LICENSE_AGREEMENT.txt ./

RUN ["chmod", "+x",  "bb_runner.sh"]
ENTRYPOINT ["/opt/gpudb/kml/bbx/bb_runner.sh"]
