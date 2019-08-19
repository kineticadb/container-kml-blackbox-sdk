#! /bin/bash

repo_uri=$(cat repo_uri.info)
importspec=$(sed 's/\"/\\\"/g' spec.json | tr -d '\n')

echo "Building and publishing to $repo_uri"

cp Dockerfile Dockerfile.WITH_SPECLABEL

echo "" >> Dockerfile.WITH_SPECLABEL
echo "LABEL kinetica.ml.import.spec=\"$importspec\""  >> Dockerfile.WITH_SPECLABEL

docker build -f Dockerfile.WITH_SPECLABEL -t $repo_uri . 

if [ "$?" -eq "0" ]
then
	echo "Docker Build Successful, Publishing container publicly"
	docker push $repo_uri
	echo "Completed building and publishing to $repo_uri"
else
 	echo "Docker Build Failed, no release executed"
fi

rm Dockerfile.WITH_SPECLABEL
