#! /bin/bash

docker build -f Dockerfile -t kinetica/kinetica-blackbox-sdk:r7.0.0.0-beta3-2 . 
docker push kinetica/kinetica-blackbox-sdk:r7.0.0.0-beta3-2