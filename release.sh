#! /bin/bash

docker build -f Dockerfile -t kinetica/kinetica-blackbox-sdk:r7.0.0.1-alpha . 
docker push kinetica/kinetica-blackbox-sdk:r7.0.0.1-alpha
