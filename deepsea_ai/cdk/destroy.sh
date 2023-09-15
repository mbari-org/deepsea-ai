#!/usr/bin/env bash
# Destroys stack in AWS
# Requires nodejs, yarn, awscli, and cdk
# Run with ./destroy.sh <path to config.yml>
# Example: ./destroy.sh config.yml
# Get the account number associated with the current IAM credentials
set -x
cd app
account=$(aws sts get-caller-identity --query Account --output text)
# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}
# Set the environment variables needed for the stack CDK_STACK_CONFIG, CDK_DEPLOY_ACCOUNT, CDK_DEPLOY_REGION
export CDK_STACK_CONFIG=$1
export CDK_DEPLOY_ACCOUNT=$account
export CDK_DEPLOY_REGION=$region
export PATH=$PATH:$(pwd)/node_modules/.bin:/usr/local/bin:/opt/homebrew/bin
# Get the short version of the hash of the commit
git_hash=$(git log -1 --format=%h)
cdk destroy --output ${git_hash}$1 --require-approval never
