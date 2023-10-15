#!/usr/bin/env bash
# Deploy ecs-autoscale stack to AWS
# Run with ./deploy.sh <path to config.yml> <path to save the output>
# Example: ./deploy.sh config.yml /tmp
set -x
# Flag an error if there are not two arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: ./deploy.sh <path to config.yml> <path to save the output>"
    exit 1
fi
cd /app
# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}

# Set the environment variables needed for the stack CDK_STACK_CONFIG, CDK_DEPLOY_ACCOUNT, CDK_DEPLOY_REGION
export CDK_STACK_CONFIG=$1
export CDK_DEPLOY_ACCOUNT=$account
export CDK_DEPLOY_REGION=$region

#export PATH=$PATH:$(pwd)/node_modules/.bin:/usr/local/bin:/opt/homebrew/bin
cdk bootstrap --output ${out_dir} && cdk synth --output ${out_dir} && cdk deploy --output ${out_dir} --require-approval never