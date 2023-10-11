FROM node:18-slim as app

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="Apache License 2.0"

ARG GIT_VERSION=latest
ARG IMAGE_URI=mbari/deepsea-ai:${GIT_VERSION}

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y openssl && \
    apt-get install -y musl-dev && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

WORKDIR /app

# Install the AWS CDK dependencies
RUN npm install -g aws-cdk

# Add the code for the stack and run
ADD deepsea_ai/cdk/app .
RUN npm install
ENTRYPOINT ["cdk","deploy","--require-approval","never"]
