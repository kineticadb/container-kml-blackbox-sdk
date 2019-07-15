#! /bin/bash

repo_uri=$(cat repo_uri.info)

docker build -f Dockerfile -t $repo_uri . 

if [ "$?" -eq "0" ]
then
	echo "Docker Build Successful, Publishing container publicly"
	docker push $repo_uri
else
 	echo "Docker Build Failed, no release executed"
fi
