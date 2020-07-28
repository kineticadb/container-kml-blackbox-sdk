#! /usr/bin/env bash

set -o nounset

# import our common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR/.."
GPUDB_DEV_DIR="$ROOT_DIR/.."
GPUDB_BUILD_DIR="${GPUDB_DEV_DIR}/gpudb-build"
source "${GPUDB_BUILD_DIR}/common/scripts/make-dist-common.sh"

# initialize our variables
UNDERSCORE_BUILD_DIR="${ROOT_DIR}/_build"
BUILD_FOLDER_NAME=""
get_build_folder_name BUILD_FOLDER_NAME
ROOT_BUILD_DIR="${UNDERSCORE_BUILD_DIR}/${BUILD_FOLDER_NAME}"
BUILD_DIR="$ROOT_BUILD_DIR/build"

GPUDB_PYTHON_API_DIR="${GPUDB_DEV_DIR}/gpudb-api-python"

LOG="$ROOT_BUILD_DIR/make-dist.log"
mkdir -p "$ROOT_BUILD_DIR"
echo > $LOG

DELETE_IMAGES=0
DOCKER_CACHE_ARG="--no-cache"
DOCKER_REGISTRY=""
PUSH=0

# define usage
function print_help
{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --docker-enable-cache: Enable caching during docker builds."
    echo "  --docker-registry <registry>: The docker registry to push to (default = docker.io)"
    echo "  --push: Push the created images after a successful build."
    echo "  --rm: Delete the images after they have been built/pushed (save on local storage)"
    echo ""
    echo "  --help (-h): Print this help."
}

# grab command line args
while [[ $# > 0 ]]; do
    key="$1"
    shift

    case $key in
        --docker-enable-cache)
            DOCKER_CACHE_ARG=""
            ;;
        --docker-registry)
            DOCKER_REGISTRY="${1}/"
            shift
            ;;
        --push)
            PUSH=1
            ;;
        --rm|--delete-images)
            DELETE_IMAGES=1
            ;;

        -h|--help)
            print_help
            exit 0
            ;;
        *)
            print_help
            echo "Unknown option: '$key', exiting."
            exit 1
    ;;
esac
done

mkdir -p ${BUILD_DIR}

# --------------------------------------------------------------------------------
# Version Information

# Grab the version info for this repo.
pushd_cmd $ROOT_DIR
    GIT_REPO_NAME=""
    get_git_repo_name "GIT_REPO_NAME"
    VERSION_INFO=""
    get_version_info "VERSION_INFO"
    VERSION=""
    get_version "VERSION"
    BUILD_NUMBER="$(get_git_build_number_with_modifications)"
popd_cmd

pushd_cmd "$GPUDB_PYTHON_API_DIR"
    PYTHON_API_VERSION_INFO=""
    get_version_info "PYTHON_API_VERSION_INFO"
    VERSION_INFO=$(printf "$VERSION_INFO\n$PYTHON_API_VERSION_INFO")
popd_cmd

THREE_DIGIT_VERSION="$(echo "$VERSION" | grep -o -E "[0-9]+\.[0-9]+\.[0-9]+" | head -n 1)"
MAJOR_VERSION="$(echo "${THREE_DIGIT_VERSION}" | awk -F. '{print $1}')"
MINOR_VERSION="$(echo "${THREE_DIGIT_VERSION}" | awk -F. '{print $2}')"

echo "VERSION=$VERSION"
echo "THREE_DIGIT_VERSION=$THREE_DIGIT_VERSION"


# --------------------------------------------------------------------------------
# Begin Build

run_cmd "${GPUDB_PYTHON_API_DIR}/build/make-wheel.sh --build-architecture $(uname -m)"

BUILD_DATE_LABEL="LABEL build_date=\"$(date +"%Y-%m-%d %T")\""

SUCCESSFUL_IMAGES=()

CONTAINER_BUILD_DIR="${BUILD_DIR}/container"
DOCKERFILE="${CONTAINER_BUILD_DIR}/Dockerfile"
IMAGE_NAME="$(sed -E "s/:r[0-9].*//g" ${ROOT_DIR}/repo_uri.info)"
DOCKER_IMAGE="${DOCKER_REGISTRY}${IMAGE_NAME}:r${THREE_DIGIT_VERSION}"

echo "Building ${DOCKER_IMAGE}..."

run_cmd "mkdir -p ${CONTAINER_BUILD_DIR}"
run_cmd "safe_rm_rf ${CONTAINER_BUILD_DIR}/*"

run_cmd "cp ${ROOT_DIR}/*.py '${CONTAINER_BUILD_DIR}'"
run_cmd "cp ${ROOT_DIR}/*.json '${CONTAINER_BUILD_DIR}'"
run_cmd "cp ${ROOT_DIR}/*.sh '${CONTAINER_BUILD_DIR}'"
run_cmd "cp -R ${ROOT_DIR}/sdk '${CONTAINER_BUILD_DIR}'"
run_cmd "cp -R '${ROOT_DIR}/requirements.txt' '${CONTAINER_BUILD_DIR}'"

run_cmd "cp -R '${GPUDB_PYTHON_API_DIR}/_build/wheel' '${CONTAINER_BUILD_DIR}/gpudb-api-python'"

run_cmd "sed -E 's/LABEL build_date=.*/${BUILD_DATE_LABEL}/g' ${ROOT_DIR}/Dockerfile > ${DOCKERFILE}"
for REQUIREMENTS in $(find ${CONATINER_BUILD_DIR} -name "requirements.txt"); do
    if grep -E "^gpudb[ \t]*[<>=]" "${REQUIREMENTS}" > /dev/null; then
        echo "Adjusting requirements file ${REQUIREMENTS}"
        run_cmd "sed -E -i 's/gpudb[ \t]*[<>=].*/gpudb>=${MAJOR_VERSION}.${MINOR_VERSION},<${MAJOR_VERSION}.$((MINOR_VERSION+1))/g' '${REQUIREMENTS}'"
    fi
done

echo "" >> ${DOCKERFILE}
echo "LABEL kinetica.ml.import.spec=\"$(cat ${ROOT_DIR}/importspce)\"" >> ${DOCKERFILE}

pushd_cmd "${CONTAINER_BUILD_DIR}"
    run_cmd "docker build ${DOCKER_CACHE_ARG} -t ${DOCKER_IMAGE} ."
popd_cmd
SUCCESSFUL_IMAGES+=("${DOCKER_IMAGE}")

if [ "${PUSH}" == "1" ]; then
    for IMAGE in "${SUCCESSFUL_IMAGES[@]}"; do
        echo "Pushing ${IMAGE}..."
        run_cmd "docker push ${IMAGE}"
    done
fi

if [ "${DELETE_IMAGES}" == "1" ]; then
    for IMAGE in "${SUCCESSFUL_IMAGES[@]}"; do
        echo "Deleting ${IMAGE}..."
        run_cmd "docker rmi -f ${IMAGE}"
    done
fi
