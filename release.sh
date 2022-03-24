#! /bin/bash

repo_uri=$(cat repo_uri.info)

echo "Building and publishing to $repo_uri"

docker build --no-cache=true -f Dockerfile -t $repo_uri .

if [ "$?" -eq "0" ]
then
	echo "Docker Build Successful, Publishing container publicly"
	docker push $repo_uri
	echo "Completed building and publishing to $repo_uri"
else
 	echo "Docker Build Failed, no release executed"
fi
