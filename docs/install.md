## Requirements
 
* [An AWS account](https://aws.amazon.com)
* [Python 3.8 or later](https://python.org/downloads/) 


**After you have setup your AWS account, confirm your AWS Account by listing your s3 buckets**

```
$ aws --version
$ aws s3 ls 
```

## Installing

Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/):

```shell
$ pip install -U deepsea-ai
```

## Set up an IAM managed policy

Use the following instructions to create an execution policy that will
grant access to use the services used in the **deepsea-ai** module.
  

Your organization may have strict which require a different role; contact your
system administrator for details on how this should be modified.

First, create a role called DeepSeaAI that has full access to S3, SageMaker, and ECS 

Allow ecs tasks to assume the role. This requires a json formatted description

```
POLICY_JSON=$(cat <<-END
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
    ]
}
END
)
```

```
aws iam create-role --role-name DeepSeaAI  --assume-role-policy-document "${POLICY_JSON}"
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## Set the SageMaker Role Environment Variable

The Amazon Resource Name (ARN) specifying the role is required to access the SageMaker API.

Fetch the ARN for the role with the ** get-role ** command

```
aws iam get-role --role-name DeepSeaAI
```

Use the Role->Arn field, e.g. *arn:aws:iam::872338704006:role/DeepSeaAI*

```
export SAGEMAKER_ROLE=arn:aws:iam::872338704006:role/DeepSeaAI
```
