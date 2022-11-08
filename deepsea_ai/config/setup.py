#!/usr/bin/env python
###########################################################################################################
# Credit to Alex for his blog: https://alexwlchan.net/2020/11/copying-images-from-docker-hub-to-amazon-ecr/
# and code detailing how to mirror repositories below
###########################################################################################################
import base64
import json
import subprocess

import boto3
from botocore.exceptions import ClientError
from deepsea_ai.config import config as cfg


def get_ecr_repo_names_in_account(ecr_client, *, account_id):
    """
    Returns a set of all the ECR repository names in an AWS account.
    """
    repo_names = set()

    paginator = ecr_client.get_paginator("describe_repositories")
    for page in paginator.paginate(registryId=account_id):
        for repo in page["repositories"]:
            repo_names.add(repo["repositoryName"])

    return repo_names


def docker_login_to_ecr(ecr_client, *, account_id):
    """
    Authenticate Docker against the ECR repository in a particular account.

    The authorization token obtained from ECR is good for twelve hours, so this
    function is cached to save repeatedly getting a token and running `docker login`
    in quick succession.
    """
    response = ecr_client.get_authorization_token(registryIds=[account_id])

    try:
        auth = response["authorizationData"][0]
    except (IndexError, KeyError):
        raise RuntimeError("Unable to get authorization token from ECR!")

    auth_token = base64.b64decode(auth["authorizationToken"]).decode()
    username, password = auth_token.split(":")

    cmd = [
        "docker",
        "login",
        "--username",
        username,
        "--password",
        password,
        auth["proxyEndpoint"],
    ]

    subprocess.check_call(cmd)


def create_ecr_repository(ecr_client, *, name):
    """
    Create a new ECR repository.
    """
    try:
        ecr_client.create_repository(repositoryName=name)
    except ClientError as err:
        if err.response["Error"]["Code"] == "RepositoryAlreadyExistsException":
            pass
        else:
            raise


def docker(*args):
    """
    Shell out to the Docker CLI.
    """
    subprocess.check_call(["docker"] + list(args))


def mirror_docker_hub_images_to_ecr(ecr_client, *, account_id, region, image_tags):
    """
    Given the name/tag of images in Docker Hub, mirror those images to ECR.
    """

    print(f"Creating all ECR repositories in account {account_id}...")
    existing_repos = get_ecr_repo_names_in_account(ecr_client, account_id=account_id)

    mirrored_repos = set(tag.split(":")[0] for tag in image_tags)
    missing_repos = mirrored_repos - existing_repos

    for repo_name in missing_repos:
        ecr_client.create_repository(repositoryName=repo_name)

    print(f"Authenticating Docker with ECR for account {account_id}...")
    docker_login_to_ecr(ecr_client, account_id=account_id)

    for hub_tag in image_tags:
        ecr_tag = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{hub_tag}"
        print(f"Mirroring {hub_tag} to {ecr_tag}")
        docker("pull", hub_tag)
        docker("tag", hub_tag, ecr_tag)
        docker("push", ecr_tag)


def create_role(account_id: str):
    """
    Sets up the IAM role called DeepSeaAI to support ECR and SageMaker
    :param account_id: AWS account ID
    """
    session = boto3.session.Session()
    iam = session.client('iam')

    path = '/'
    role_name = 'DeepSeaAI'
    description = 'DeepSeaAI Role'
    session_secs = 43200

    ASSUME_ROLE_POLICY_JSON = {
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

    ROLE_PERMISSIONS_JSON =  {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "iam:GetRole",
                    "iam:PassRole"
                ],
                "Resource": f"arn:aws:iam::{account_id}:role/{role_name}"
            }]
    }

    try:

        policy = f"{role_name}GetAndPassRolePolicy"

        iam = session.client('iam')

        resource = iam.create_policy(
            PolicyName=policy,
            PolicyDocument=json.dumps(ROLE_PERMISSIONS_JSON)
        )

        iam.create_role(
            Path=path,
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(ASSUME_ROLE_POLICY_JSON),
            Description=description,
            MaxSessionDuration=session_secs
        )

        iam.attach_role_policy(
            PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
            RoleName=role_name
        )
        iam.attach_role_policy(
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess',
            RoleName=role_name
        )
        iam.attach_role_policy(
            PolicyArn=f"arn:aws:iam::aws:policy/{policy}",
            RoleName=role_name
        )

    except ClientError as err:
        if err.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"Role {role_name} already exists.")
            pass
        else:
            raise


def store_role(config: cfg):
    """
    Save the role in the config
    """
    session = boto3.session.Session()
    iam = session.client('iam')
    results = iam.get_role(RoleName="DeepSeaAI")
    role_arn = results['Role']['Arn']
    print(f'Setting SageMaker Role ARN to {role_arn} in {config.path}')
    config.save('aws', 'sagemaker_arn', role_arn)


if __name__ == "__main__":
    default_config = cfg.Config()
    default_config_ini = cfg.default_config_ini
    account = default_config.get_account()
    region = default_config.get_region()
    image_cfg = ['yolov5_ecr', 'deepsort_ecr', 'strongsort_ecr']
    image_tags = [default_config('aws', t) for t in image_cfg]
    mirror_docker_hub_images_to_ecr(ecr_client=boto3.client("ecr"), account_id=account, region=region, image_tags=image_tags)
    create_role(account_id=account)
    store_role(default_config)

