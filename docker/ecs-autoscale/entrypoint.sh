#!/usr/bin/env bash
# Deploy ecs-autoscale stack to AWS
# Run with ./deploy.sh <path to config.yml> <path to save the output>
# Example: ./deploy.sh config.yml /tmp
set -x
# Flag an error if there are not two arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: ./deploy.sh <path to config.yml> <path to save cdk output>"
    exit 1
fi

# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}

# Set the environment variables needed for the stack CDK_STACK_CONFIG, CDK_DEPLOY_ACCOUNT, CDK_DEPLOY_REGION
export CDK_STACK_CONFIG=$1
export CDK_DEPLOY_ACCOUNT=$account
export CDK_DEPLOY_REGION=$region

# If there is a second argument, use it as the output directory
if [ "$#" -eq 2 ]; then
    cdk bootstrap --output $2 && cdk synth --output $2 && cdk deploy --output $2 --require-approval never
    exit 0
else
    cdk bootstrap && cdk synth && cdk deploy --require-approval never
fi