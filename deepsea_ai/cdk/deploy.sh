#!/usr/bin/env bash
# Deploy stack to AWS
# Requires nodejs, yarn, awscli, and cdk
# Useful for testing changes to the stack
# Run with ./deploy.sh <path to config.yml>
# Example: ./deploy.sh config.yml
set -x
cd app
# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)
# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}
# Set the environment variables needed for the stack CDK_STACK_CONFIG, CDK_DEPLOY_ACCOUNT, CDK_DEPLOY_REGION
export CDK_STACK_CONFIG=$1
export CDK_DEPLOY_ACCOUNT=$account
export CDK_DEPLOY_REGION=$region
export PATH=$PATH:$(pwd)/node_modules/.bin:/usr/local/bin:/opt/homebrew/bin
npm -g uninstall aws-cdk
npm -g install aws-cdk
npm build
# Get the short version of the hash of the commit
git_hash=$(git log -1 --format=%h)
out_dir=${git_hash}$1
cdk bootstrap --output ${out_dir} && cdk synth --output ${out_dir} && cdk deploy --output ${out_dir}
