# Kinetica Blackbox SDK build
#
# SDK for containerized models with usage examples
#
# Kinetica Machine Learning (KML)
# (c) 2023 Kinetica DB, Inc.

# Base image
FROM python:3.11.3-slim-bullseye

# Image labels
LABEL maintainer="support@kinetica.com"
LABEL Description="Kinetica model blackbox SDK with examples"

# Model path
RUN mkdir -p /opt/gpudb/kml
WORKDIR "/opt/gpudb/kml"

# Model introspection manifest
ADD spec.json  ./

# Required libraries and dependencies
ADD requirements.txt  ./
RUN pip install --upgrade pip
#RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir

# Kinetica BlackBox SDK
ADD bb_runner.sh ./
ADD sdk ./sdk

# Module files [user editable]
ADD bb_module_default.py ./
ADD bb_module_temperature.py ./

# Additional resources [user editable]
# ADD my_model_binary.pkl ./
# ADD my_resouce_file.csv ./

# EULA
ADD END_USER_LICENSE_AGREEMENT.txt ./

# Container entrypoint
RUN ["chmod", "+x",  "bb_runner.sh"]
ENTRYPOINT ["/opt/gpudb/kml/bb_runner.sh"]
