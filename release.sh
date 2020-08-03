#! /bin/bash

repo_uri=$(cat repo_uri.info)
dt=`date +"%Y-%m-%d %T"`
build_str="LABEL build_date=\"$dt\""
match="LABEL build_date=.*"


importspec=$(sed 's/\"/\\\"/g' spec.json | tr -d '\n')

echo "Building and publishing to $repo_uri"

cp Dockerfile Dockerfile.WITH_SPECLABEL

echo "" >> Dockerfile.WITH_SPECLABEL
echo "LABEL kinetica.ml.import.spec=\"$importspec\""  >> Dockerfile.WITH_SPECLABEL

sed -i "s/$match/$build_str/" Dockerfile.WITH_SPECLABEL

docker build --no-cache=true -f Dockerfile.WITH_SPECLABEL -t $repo_uri .

if [ "$?" -eq "0" ]
then
	echo "Docker Build Successful, Publishing container publicly"
	docker push $repo_uri
	echo "Completed building and publishing to $repo_uri"
else
 	echo "Docker Build Failed, no release executed"
fi

rm Dockerfile.WITH_SPECLABEL
echo $dt" -- "$repo_uri >> docker_release.log