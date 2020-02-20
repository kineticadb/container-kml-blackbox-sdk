#! /bin/bash

repo_uri=$(cat repo_uri.info)
dt=`date +"%Y-%m-%d %T"`
build_str="LABEL build_date=\"$dt\""
match="LABEL build_date=.*"

echo $dt" -- "$repo_uri >> docker_release.log
sed -i "s/$match/$build_str/" Dockerfile

# Removed since Docker Daemon cant handle overly complex double escaped json files for specs
#python -m sdk.prepper --spec-in spec.json --spec-out spec_enriched.json
#importspec=$(sed 's/\"/\\\"/g' spec_enriched.json | tr -d '\n')

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

# Removed since Docker Daemon cant handle overly complex double escaped json files for specs
#rm spec_enriched.json
