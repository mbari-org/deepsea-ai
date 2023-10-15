FROM node:18-slim as app

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="Apache License 2.0"

ARG GIT_VERSION=latest
ARG IMAGE_URI=mbari/ecs-autoscale:${GIT_VERSION}

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y openssl && \
    apt-get install -y musl-dev && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

# Add the code for the stack and clean-up
WORKDIR /tmp

#RUN #git clone https://github.com/mbari-org/deepsea-ai.git app
RUN if [ "$GIT_VERSION" != "latest" ]; then \
    git clone --branch $GIT_VERSION --depth 1 https://github.com/mbari-org/deepsea-ai.git app; \
    else \
    git clone https://github.com/mbari-org/deepsea-ai.git app; \
    fi

WORKDIR /app
RUN mv /tmp/app/deepsea_ai/cdk/app . && \
    rm -rf /tmp/app \

# Install the required node modules
RUN npm install
ENTRYPOINT [ "/app/entrypoint.sh" ]