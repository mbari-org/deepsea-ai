#!/usr/bin/env bash
# Build and push docker image with needed dependencies to the docker hub
# Run with ./build_and_push_dockerhub.sh
# This will build and upload the image mbari/ecs-autoscale:<hash>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$(dirname "${SCRIPT_DIR}/../" )" && pwd )"
cd $BASE_DIR
set -x

# The name of our algorithm
algorithm_name=ecs-autoscale

# Get the short version of the hash of the commit
git_hash=$(git log -1 --format=%h)

# Build and push it to docker hub with the full name
docker build --no-cache --label GIT_COMMIT=$git_hash --build-arg IMAGE_URI=mbari/${algorithm_name}:$git_hash  --platform linux/amd64 -t mbari/${algorithm_name}:$git_hash .
docker push mbari/${algorithm_name}:$git_hash
