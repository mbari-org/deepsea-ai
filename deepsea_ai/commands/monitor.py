# !/usr/bin/env python
__author__ = "Danelle Cline, Duane Edgington"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Various commands for monitoring the status of processing or training jobs

@author: __author__
@status: __status__
@license: __license__
'''

import boto3

from deepsea_ai.logger import info


def print_scaling_activities(resources: dict, num_records: int = 10):
    """
    Print scaling activities for a given resource
    """
    client = boto3.client('autoscaling')
    response = client.describe_scaling_activities(
        ActivityIds=[],
        AutoScalingGroupName=resources['ASG'],
        IncludeDeletedGroups=False,
        MaxRecords=num_records)

    for i in response['Activities']:
        info(f'{i["StartTime"]} {i["Description"]}  {i["Cause"]}')


def print_queue_status(resources: dict):
    """
    Print the status of the queue
    """
    client = boto3.client('sqs')
    queues = ['TRACK_QUEUE', 'VIDEO_QUEUE', 'DEAD_QUEUE']
    processor = resources['PROCESSOR']
    for q in queues:
        response = client.get_queue_attributes(
            QueueUrl=resources[q],
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'])
        if q == 'TRACK_QUEUE':
            info(
                f'{processor}:{q} number of completed videos: {response["Attributes"]["ApproximateNumberOfMessages"]} ')
        if q == 'VIDEO_QUEUE':
            info(
                f'{processor}:{q} number of videos to process: {response["Attributes"]["ApproximateNumberOfMessages"]},'
                f' number of videos in progress: {response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')
        if q == 'DEAD_QUEUE':
            info(
                f'{processor}:{q} number of videos that failed to process: {response["Attributes"]["ApproximateNumberOfMessages"]}')
