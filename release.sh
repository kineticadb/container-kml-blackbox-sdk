#! /bin/bash

docker build -f Dockerfile -t kinetica/kinetica-blackbox-sdk:r7.0.5b . 
docker push kinetica/kinetica-blackbox-sdk:r7.0.5b
