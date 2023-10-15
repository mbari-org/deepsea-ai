#!/usr/bin/env bash
# Build and push docker image with needed dependencies to the docker hub
# Run with ./build_and_push_dockerhub.sh
# This will build and upload the images for development purposes:
# mbari/ecs-autoscale:<hash>
# mbari/deepsea-aie:<hash>
set -x
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$(dirname "${SCRIPT_DIR}/../../" )" && pwd )"
cd $BASE_DIR

containers=(ecs-autoscale deepsea-ai)

# Get the short version of the hash of the commit
git_hash=$(git log -1 --format=%h)

for container in "${containers[@]}"
do
    docker build --label GIT_COMMIT=$git_hash \
    --build-arg IMAGE_URI=mbari/${container}:$git_hash \
    --platform linux/amd64 \
    -t mbari/${container}:$git_hash \
    -f docker/${container} .
done
