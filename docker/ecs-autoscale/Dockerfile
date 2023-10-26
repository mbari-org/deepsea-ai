FROM node:18-slim as app

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="Apache License 2.0"

ARG GIT_VERSION=latest
ARG IMAGE_URI=mbari/ecs-autoscale:${GIT_VERSION}

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y curl && \
    apt-get install -y openssl && \
    apt-get install -y musl-dev && \
    apt-get install -y unzip && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1 && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf \
        awscliv2.zip \
    && apt-get -y purge curl \
    && apt-get -y purge unzip

WORKDIR /tmp

RUN if [ "$GIT_VERSION" != "latest" ]; then \
    git clone -b v${GIT_VERSION} --depth 1 https://github.com/mbari-org/deepsea-ai.git app; \
    else \
    git clone --depth 1 https://github.com/mbari-org/deepsea-ai.git app; \
    fi

WORKDIR /app

RUN mv /tmp/app/deepsea_ai/cdk/app/* . && \
    mv /tmp/app/docker/ecs-autoscale/entrypoint.sh . && \
    rm -rf /tmp/app

RUN chmod +x entrypoint.sh

# Install the required node modules
RUN npm install && npm install -g aws-cdk

ARG DOCKER_GID=998
ARG DOCKER_UID=582

# Create a user with a specific UID and GID and add to docker group
RUN groupadd -g ${DOCKER_GID} docker && \
    useradd -u ${DOCKER_UID} -g ${DOCKER_GID} -m docker_user

RUN chown -R docker_user:docker /home/docker_user && \
    chown -R docker_user:docker /app

# Run as the docker user
USER docker_user

RUN export PATH=$PATH:/app/node_modules/.bin
ENTRYPOINT [ "/app/entrypoint.sh" ]
