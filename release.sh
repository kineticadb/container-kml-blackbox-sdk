#! /bin/bash

docker build -f Dockerfile -t kinetica/kinetica-blackbox-sdk:r7.0.5 . 

if [ "$?" -eq "0" ]
then
	echo "Docker Build Successful, Publishing container publicly"
	docker push kinetica/kinetica-blackbox-sdk:r7.0.5
else
 	echo "Docker Build Failed, no release executed"
fi
