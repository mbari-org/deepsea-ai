## Set up an IAM managed policy

Use the following instructions to create an execution policy that will
grant access to use the services used in the *deepsea-ai* module.

**You can safely skip this if you have run the ```deepsea-ai setup``` command which will do this for you**

Batch processing uses the Elastic Container Service (ECS) which requires permissions
for the tasks that run the detection and processing pipelines to assume the role.

Training uses SageMaker which requires permissions for the trainer to assume the role.

This requires a JSON formatted description which can be created with

```shell
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
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
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

### Attach permission to allow full access to S3 and SageMaker to the policy

This will allow permission to create S3 buckets, to store and remove artifacts in the bucket, and, finally, 
full access to the SageMaker API for training and processing.

```shell
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name DeepSeaAI --policy-arn  arn:aws:iam::aws:policy/AmazonS3FullAccess
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

**You can safely skip this if you have run the ```deepsea-ai setup``` command which will do this for you**

Use the field returned called "Arn", for example *arn:aws:iam::12345678911:role/DeepSeaAI* to set the environment
variable SAGEMAKER_ROLE

```shell
export SAGEMAKER_ROLE=arn:aws:iam::872338704006:role/DeepSeaAI
```
