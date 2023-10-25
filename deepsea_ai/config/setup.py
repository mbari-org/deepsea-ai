# deepsea-ai, Apache-2.0 license
# Filename: config/setup.py
# Description: Setup utility for mirror docker images to ECR, create role, and setup default data
###########################################################################################################
# Credit to Alex for his blog: https://alexwlchan.net/2020/11/copying-images-from-docker-hub-to-amazon-ecr/
# and code detailing how to mirror repositories below
###########################################################################################################
import base64
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from deepsea_ai.config import config as cfg
from deepsea_ai.config.config import Config
from deepsea_ai.logger import err, info, warn, exception


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
            exception(err)
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

    info(f"Creating all ECR repositories in account {account_id}...")
    existing_repos = get_ecr_repo_names_in_account(ecr_client, account_id=account_id)

    mirrored_repos = set(tag.split(":")[0] for tag in image_tags)
    missing_repos = mirrored_repos - existing_repos

    for repo_name in missing_repos:
        ecr_client.create_repository(repositoryName=repo_name)

    info(f"Authenticating Docker with ECR for account {account_id}...")
    docker_login_to_ecr(ecr_client, account_id=account_id)

    for hub_tag in image_tags:
        ecr_tag = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{hub_tag}"
        info(f"Mirroring {hub_tag} to {ecr_tag}")
        docker("pull", hub_tag)
        docker("tag", hub_tag, ecr_tag)
        docker("push", ecr_tag)


def create_role(account_id: str):
    """
    Sets up the IAM role called DeepSeaAI to support ECR, SageMaker, and ECS
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

    ROLE_PERMISSIONS_JSON = {
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

        iam.create_policy(
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
            PolicyArn='arn:aws:iam::aws:policy/AWSCloudFormationFullAccess',
            RoleName=role_name
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
            warn(f"Role {role_name} already exists.")
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
    info(f'Setting SageMaker Role ARN to {role_arn} in {config.config_ini}')
    config.save('aws', 'sagemaker_arn', role_arn)
    # Parse the ARN to get the account ID
    account_id = role_arn.split(':')[4]
    config.save('aws', 'account_id', account_id)


def download_s3_file(bucket: str, key: str, local_path: Path) -> bool:
    """
    Download a file from s3 to a local path
    :param bucket:  Bucket name
    :param key: prefix/key to the object
    :param local_path: Local path to save the file
    :return:  True if successful, False otherwise
    """
    try:
        info(f'Downloading s3://{bucket}/{key} to {local_path.as_posix()}')
        s3 = boto3.resource('s3', region_name='us-west-2')
        s3.Bucket(bucket).download_file(key, local_path.as_posix())
        return True
    except Exception as ex:
        print(f'Exception {ex}')
        return False


def make_bucket(bucket: str, region: str) -> bool:
    """
    Create a bucket if it doesn't exist
    :param bucket: Bucket name
    :param region: Region name
    :return: True if successful, False otherwise
    """
    s3 = boto3.client('s3', region_name=region)
    try:
        info(f'Creating bucket {bucket} in {region}')
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': region})
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            warn(f"Bucket {bucket} already exists.")
            return True
        else:
            raise


def setup_default_data(config: Config):
    """
    Setup default data, including video, models, and  track config.
    This creates default data in the following buckets:
    deepsea-ai-<account>-models
    deepsea-ai-<account>-track-conf
    deepsea-ai-<account>-videos
    deepsea-ai-<account>-tracks
    """
    default_model_s3 = config('aws_public', 'model')
    default_track_s3 = config('aws_public', 'track_config')
    account = config.get_account()

    # Create the buckets if they don't exist
    buckets = [f'deepsea-ai-{account}-models',
               f'deepsea-ai-{account}-track-conf',
               f'deepsea-ai-{account}-videos',
               f'deepsea-ai-{account}-tracks']
    for bucket in buckets:
        if not make_bucket(bucket, 'us-west-2'):
            err(f'Cannot create bucket {bucket}')
            return

    # Save the buckets in the config
    config.save('aws', 'models', f's3://{buckets[0]}')
    config.save('aws', 'track_config', f's3://{buckets[1]}')
    config.save('aws', 'videos', f's3://{buckets[2]}')
    config.save('aws', 'tracks', f's3://{buckets[3]}')

    # Download data from S3 to a temp directory and then upload to the new buckets
    with tempfile.TemporaryDirectory() as temp_dir:

        ###########################################################################################
        # Handle video defaults
        ###########################################################################################
        for v in ['video_ex1', 'video_ex2', 'video_ex3']:
            # Parse the s3 path of the default to download
            src = urlparse(config('aws_public', v))
            tgt = urlparse(f's3://{buckets[2]}/{Path(src.path).name}')

            # Skip if the file already exists
            s3 = boto3.resource('s3')
            bucket_tgt = s3.Bucket(tgt.netloc)
            found = False
            for obj in bucket_tgt.objects.all():
                if Path(src.path).name in obj.key:
                    info(f'Found {Path(src.path).name} in {tgt.netloc} so skipping')
                    found = True

            if not found:
                # Download the file from the source bucket
                out_path = Path(temp_dir) / Path(src.path).name
                if not download_s3_file(src.netloc, src.path.lstrip('/'), out_path):
                    err(f'Cannot find {s3}')
                    return
                else:
                    info(f'Uploading {out_path.as_posix()} to {tgt.netloc}')
                    s3.Bucket(tgt.netloc).upload_file(out_path.as_posix(), out_path.name)

        ###########################################################################################
        # Handle model and track config defaults
        ###########################################################################################

        # Dictionary of defaults and their associated buckets to upload to
        defaults = {default_model_s3: f"s3://{buckets[0]}", default_track_s3: f"s3://{buckets[1]}"}

        for bucket_source, bucket_target in defaults.items():
            # Parse the s3 path of the default to download
            src = urlparse(bucket_source)
            tgt = urlparse(bucket_target)

            # Skip if the file already exists
            s3 = boto3.resource('s3')
            bucket_tgt = s3.Bucket(tgt.netloc)
            found = False
            for obj in bucket_tgt.objects.all():
                if Path(src.path).name in obj.key:
                    info(f'Found {Path(src.path).name} in {bucket_target} so skipping')
                    if 'model' in bucket_target:
                        config.save('aws', 'model', f'{bucket_target}/{Path(src.path).name}')
                    elif 'track' in bucket_target:
                        config.save('aws', 'track_config', f'{bucket_target}/{Path(src.path).name}')
                    found = True

            if not found:
                # Download the file from the source bucket
                out_path = Path(temp_dir) / Path(src.path).name
                if not download_s3_file(src.netloc, src.path.lstrip('/'), out_path):
                    err(f'Cannot find {s3}')
                    return
                else:
                    info(f'Uploading {out_path.as_posix()} to {bucket_target}')
                    s3.Bucket(tgt.netloc).upload_file(out_path.as_posix(), out_path.name)


if __name__ == "__main__":
    default_config = cfg.Config()
    default_config_ini = cfg.default_config_ini
    account = default_config.get_account()
    region = default_config.get_region()
    image_cfg = ['yolov5_container', 'strongsort_container']
    image_tags = [default_config('docker', t) for t in image_cfg]
    mirror_docker_hub_images_to_ecr(ecr_client=boto3.client("ecr"), account_id=account, region=region,
                                    image_tags=image_tags)
    create_role(account_id=account)
    store_role(default_config)
    setup_default_data(default_config)
