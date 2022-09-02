# !/usr/bin/env python
__author__ = "Danelle Cline, Duane Edgington"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Configuration helper to setup defaults and fetch cloud configuration

@author: __author__
@status: __status__
@license: __license__
'''

import boto3
import datetime as dt
import os
from botocore.exceptions import ClientError
from pathlib import Path
from typing import List

default_training_prefix = 'training'

def get_role():
    """
    Get the user role or default to an MBARI generated one
    :return
    """
    if 'SAGEMAKER_ROLE' not in os.environ:
        raise Exception(f"SAGEMAKER_ROLE must be set in your environment variables")
    return os.environ['SAGEMAKER_ROLE']

def get_account() -> str:
    """
    Get the account number associated with this user
    :return:
    """
    account_number = boto3.client('sts').get_caller_identity()['Account']
    print(f'Found account {account_number}')
    return account_number


def get_username() -> str:
    """
    Get the user name using IAM; if IAM is not configured, this will default to the root user which may be the case
    for a new AWS account
    :return:
    """
    try:
        iam = boto3.client('iam')
        if 'UserName' in iam.get_user()["User"]:
            user_name = iam.get_user()["User"]["UserName"]
        else:
            user_name = 'root'
    except ClientError as e:
        # The user_name may be specified in the Access Denied message...
        user_name = e.response["Error"]["Message"].split(" ")[-1]

    return user_name


def get_tags() -> dict:
    """
    Configure tag dictionary to associate with a job.
    This is useful for cost accounting and general reporting
    :return:
    """
    user_name = get_username()
    deletion_date = (dt.datetime.utcnow() + dt.timedelta(days=90)).strftime('%Y%m%dT%H%M%SZ')
    tag_dict = [{'Key': 'mbari:project-number', 'Value': '902005'},
                {'Key': 'mbari:owner', 'Value': user_name},
                {'Key': 'mbari:description', 'Value': 'test pipeline'},
                {'Key': 'mbari:customer-project', 'Value': '902005'},
                {'Key': 'mbari:stage', 'Value': 'test'},
                {'Key': 'mbari:application', 'Value': 'detection'},
                {'Key': 'mbari:deletion-date', 'Value': deletion_date},
                {'Key': 'mbari:created-by', 'Value': user_name}]
    return tag_dict


def check_videos(input_path: Path) -> List[Path]:
    """
     Check for videos with acceptable suffixes and return the Paths to them
    :param input_path: input path to search (non-recursively)
    :return:
    """
    vid_formats = ['.mov', '.avi', '.mp4', '.mpg', '.mpeg', '.m4v', '.wmv', '.mkv']  # acceptable video suffixes
    files = sorted(input_path.glob('**/*'))
    videos = [x for x in files if x.suffix.lower() in vid_formats and '._' not in x.name]
    num_videos = len(videos)
    assert (num_videos > 0), "No videos to process"
    video_paths = [Path(x) for x in videos]
    return video_paths


def get_resources(stack_name: str) -> dict:
    """
    Get resources relevant to the pipeline from the stack name; see deepsea-ai/cluster/stacks
    :param stack_name:
    :return:
    """
    client_cf = boto3.client('cloudformation')
    client_ecs = boto3.client('ecs')

    stack_resources = client_cf.list_stack_resources(StackName=stack_name)
    resources = {'CLUSTER': stack_name}

    # fetch the PROCESSOR environment variable for the single task in the stack; the job is keyed uniquely to it
    key = ['PROCESSOR', 'TRACK_QUEUE', 'VIDEO_QUEUE', 'DEAD_QUEUE', 'TRACK_BUCKET', 'VIDEO_BUCKET']
    for r in stack_resources['StackResourceSummaries']:
        if 'AWS::ECS::TaskDefinition' in r['ResourceType']:
            arn = r['PhysicalResourceId']
            task_def = client_ecs.describe_task_definition(taskDefinition=arn)
            environment = task_def['taskDefinition']['containerDefinitions'][0]['environment']
            for e in environment:
                for k in key:
                    if k in e['name']:
                        resources[k] = e['value']
            break
    print(resources)
    return resources
