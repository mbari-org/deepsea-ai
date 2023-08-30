
# Welcome to your CDK TypeScript project

This is a blank project for CDK development with TypeScript.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template


# Developer Notes
- API reference and developer guide https://docs.aws.amazon.com/cdk/api/v2/
- Best practices for CDK https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html
- Asset guide https://docs.aws.amazon.com/cdk/v2/guide/assets.html . Useful for understanding S3, Lambda, and Docker assets
- Best practice examples using SPOT instances https://github.com/awslabs/ec2-spot-labs
- Nice full-stack app for scaling/monitoring https://github.com/awslabs/scale-out-computing-on-aws
- [Gist with scaling up/down example](https://gist.githubusercontent.com/gandroz/1927f37bdb1427fdf0c641b8bbcd6f3d/raw/a42dcd4cee496090c87b03d68c0b22c02d358ffe/my_stack.py)
  

## To force the deletion of a stack

- Create an IAM role that can do this, e.g. cloudformation-omnipotent
- Delete a stack from the command line with

```
aws cloudformation delete-stack --role-arn arn:aws:iam::872338704006:role/cloudformation-omnipotent --stack-name SimStack902005

```
## To use a specific AWS profile with the awscli
```
export AWS_PROFILE mbari
```
