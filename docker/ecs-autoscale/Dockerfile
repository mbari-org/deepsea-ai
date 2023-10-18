FROM node:18-slim as app

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="Apache License 2.0"

ARG GIT_VERSION=latest
ARG IMAGE_URI=mbari/ecs-autoscale:${GIT_VERSION}

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y python3-pip && \
    apt-get install -y openssl && \
    apt-get install -y musl-dev && \
    apt-get install -y unzip && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

# Install AWS CLI using pip
RUN pip3 install --upgrade pip
RUN pip3 install awscli

WORKDIR /tmp

RUN if [ "$GIT_VERSION" != "latest" ]; then \
    git clone --branch $GIT_VERSION --depth 1 https://github.com/mbari-org/deepsea-ai.git app; \
    else \
    git clone https://github.com/mbari-org/deepsea-ai.git app; \
    fi

WORKDIR /app

RUN mv /tmp/app/deepsea_ai/cdk/app/* . && \
    mv /tmp/app/docker/ecs-autoscale/entrypoint.sh . && \
    rm -rf /tmp/app

ADD entrypoint.sh .
RUN chmod +x entrypoint.sh

# Install the required node modules
RUN npm install && npm install -g aws-cdk

RUN export PATH=$PATH:/app/node_modules/.bin
ENTRYPOINT [ "/app/entrypoint.sh" ]