# Copyright (c) 2020 Kinetica DB Inc.
#
# Kinetica Machine Learning
# Kinetica Machine Learning BlackBox Container SDK + Trivial Sample
#
# for support, contact Saif Ahmed (support@kinetica.com)
#

FROM python:3.6

LABEL build_date="2020-04-07 13:00:28"
LABEL maintainer="support@kinetica.com"
LABEL Description="Kinetica Machine Learning BlackBox SDK and starter examples."
LABEL Author="Saif Ahmed; Julian Jenkins"

RUN apt-get update && apt-get install -y \
  apt-utils \
  nano \
  curl \
  wget \
  htop \
  nmon \
  vim \
  httpie \
  && apt-get clean -y

RUN mkdir -p /opt/gpudb/kml/bbx
RUN mkdir -p /opt/gpudb/kml/bbx/specs
WORKDIR "/opt/gpudb/kml/bbx"

# Install Required Libraries and Dependencies
ADD requirements.txt  ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir

# Add introspection assets
ADD *.json ./specs/

# Add Kinetica BlackBox SDK
ADD bb_runner.sh ./
ADD sdk ./sdk

ADD bb_module_default.py ./
ADD bb_module_temperature.py ./
ADD bb_module_tests.py ./


RUN ["chmod", "+x",  "bb_runner.sh"]
ENTRYPOINT ["/opt/gpudb/kml/bbx/bb_runner.sh"]
