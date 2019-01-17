#! /bin/bash

# Build first
docker build -f Dockerfile -t kinetica-blackbox-sdk . 

# Then publish
docker tag kinetica-blackbox-sdk kinetica/kinetica-blackbox-sdk
docker push kinetica/kinetica-blackbox-sdk
docker tag kinetica-blackbox-sdk kinetica/kinetica-blackbox-sdk
