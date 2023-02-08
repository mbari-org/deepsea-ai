## Setup

The  ```deepsea-ai setup``` command does a number of things under-the-hood which are detailed below 
for the advanced AWS user.  

**You can safely skip these steps if you have run the ```deepsea-ai setup``` command which will do this for you**

## Set up an IAM managed policy

Use the following instructions to create an execution policy that will
grant access to use the services used in the *deepsea-ai* module.


Batch processing ```deepsea-ai process or deepsea-ai ecsprocess``` uses the Elastic Container Service (ECS) which requires permissions
for the tasks that run the detection and processing pipelines to assume the role.

Training uses SageMaker which requires permissions for the trainer to assume the role.

This requires a JSON formatted description which can be created with

```shell
ASSUME_ROLE_POLICY_JSON=$(cat <<-END
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
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
        "Sid": "TrustPolicyStatementThatAllowsEC2ServiceToAssumeTheAttachedRole",
        "Effect": "Allow",
        "Principal": {
            "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }
    ]
}
END
)
```

### Create a role called *DeepSeaAI* using the policy
```shell
aws iam create-role --role-name DeepSeaAI  --assume-role-policy-document "${POLICY_JSON}"
```

### Create a policy called *DeepSeaAI* with the following permissions, replacing the account number with your own
```shell
ROLE_PERMISSIONS_JSON=$(cat <<-END
{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "iam:GetRole",
                    "iam:PassRole"
                ],
                "Resource": "arn:aws:iam::{account_id}:role/DeepSeaAI"
            }]
    }
END
```

```shell
aws iam create-policy --policy-name DeepSeaAIGetAndPassRolePolicy  --policy-document "${ROLE_PERMISSIONS_JSON}"

```
### Attach permission to allow full access to S3 and SageMaker to the policy

This will allow permission to create S3 buckets, to store and remove artifacts in the bucket, and, finally, 
full access to the SageMaker API for training and processing.

```shell
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::{account_id}:role/DeepSeaAIGetAndPassRolePolicy
```

## Set the SageMaker Role Environment Variable

Now that the IAM permissions are set, use the the Amazon Resource Name (ARN) for this policy
by setting its ARN in the expected environment variable SAGEMAKER_ROLE.

Fetch the role with the **get-role** command

```shell
aws iam get-role --role-name DeepSeaAI
```

This will return a JSON formatted string similar to this

```text
{
    "Role": {
        "Path": "/",
        "RoleName": "DeepSeaAI",
        "RoleId": "AROA4WG3QI2DF3XXXXB",
        "Arn": "arn:aws:iam::12345678911:role/DeepSeaAI",
        "CreateDate": "2022-10-12T19:41:50Z",
        "AssumeRolePolicyDocument": {
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
        },
        "MaxSessionDuration": 3600,
        "RoleLastUsed": {}
    }
}
```

## Set the SAGEMAKER_ROLE environment variable

Use the field returned called "Arn", for example *arn:aws:iam::12345678911:role/DeepSeaAI* to set the environment
variable SAGEMAKER_ROLE

```shell
export SAGEMAKER_ROLE=arn:aws:iam::12345678911:role/DeepSeaAI
```
