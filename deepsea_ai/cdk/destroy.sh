#!/usr/bin/env bash
# Destroys stack in AWS
# Requires nodejs, yarn, awscli, and cdk
# Run with ./destroy.sh
# Get the account number associated with the current IAM credentials
set -x
cd app
account=$(aws sts get-caller-identity --query Account --output text)
# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}
# Set the environment variables needed for the stack CDK_STACK_CONFIG, CDK_DEPLOY_ACCOUNT, CDK_DEPLOY_REGION
export CDK_STACK_CONFIG=config.yml
export CDK_DEPLOY_ACCOUNT=$account
export CDK_DEPLOY_REGION=$region
export PATH=$PATH:$(pwd)/node_modules/.bin:/usr/local/bin:/opt/homebrew/bin
cdk destroy