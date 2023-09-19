FROM node:18-slim as app

LABEL vendor="MBARI"
LABEL maintainer="dcline@mbari.org"
LABEL license="GPL"

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y openssl && \
    apt-get install -y musl-dev && \
    apt-get install -y python3 python3-pip && \
    pip3 install --upgrade pip && \
    pip3 install --no-cache-dir awscli && \
    ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

# Install the AWS CDK dependencies
RUN npm install -g aws-cdk
RUN pip3 install aws-cdk.cdk aws-cdk-lib>2.0.0 constructs>=10.0.0
RUN ln -s /usr/bin/python3 /usr/bin/python

# Add the code for the stack and run
ADD app .
RUN npm install
ENTRYPOINT ["cdk","deploy","--require-approval","never"]