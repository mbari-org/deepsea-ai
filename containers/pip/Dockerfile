FROM python:3.10-alpine

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="Apache License 2.0"

ARG GIT_VERSION=latest
ARG IMAGE_URI=mbari/deepsea-ai:${GIT_VERSION}
ARG DOCKER_GID=998
ARG DOCKER_UID=582

# Create a user with a specific UID and GID.
RUN addgroup -g ${DOCKER_GID} docker && \
    adduser -D -u ${DOCKER_UID} -G docker docker_user

# Create a virtual environment for the application dependencies.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create default directories for the application and another for the sqlite database
WORKDIR /app
RUN mkdir /sqlite
RUN pip install --upgrade deepsea-ai
RUN chown -R docker_user:docker /app /sqlite /usr/local/lib/python3.9
USER docker_user

ENTRYPOINT ["deepsea-ai"]
