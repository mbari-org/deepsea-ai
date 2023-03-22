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

import json
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

import boto3
from botocore.exceptions import ClientError

from deepsea_ai.logger import info, warn, debug, exception, err
from deepsea_ai.logger.job_cache import JobStatus, JobCache


def log_scaling_activities(resources: dict, num_records: int = 10) -> int:
    """
    Log scaling activities for a given resource
    :param resources: Dictionary of resources
    :param num_records: Number of records to return
    :param report: If true, log the activities
    :return: Number of activities
    """
    client = boto3.client('autoscaling')
    response = client.describe_scaling_activities(
        ActivityIds=[],
        AutoScalingGroupName=resources['ASG'],
        IncludeDeletedGroups=False,
        MaxRecords=num_records)

    for i in response['Activities']:
        msg = f'{i["StartTime"]} {i["Description"]}  {i["Cause"]}'
        info(msg)

    return len(response['Activities'])


def parse_message(message: dict, embed: bool = False) -> dict:
    """
    Parse the message from the queue body
    :param message: Message from the queue
    :param embed: If true, the message is a json embedded within a json
    :return: Dictionary of the message with video, job, and timestamp
    """
    if embed:
        b = json.loads(json.loads(message['Body']))
    else:
        b = json.loads(message['Body'])
    # get the video name which is the video id split from the .tracks.tar.gz
    # assume this is a mp4 video
    video = b['video']
    job = b['job_name'] if 'job_name' in b else 'unknown'
    utc_secs = int(message['Attributes']['ApproximateFirstReceiveTimestamp'])
    timestamp = datetime.utcfromtimestamp(utc_secs / 1000)
    return {'video': video, 'job': job, 'timestamp': timestamp.strftime('%Y%m%dT%H%M%S')}


def log_queue_status(resources: dict) -> dict:
    """
    Logs the status of the queue
    :param resources: Dictionary of resources
    :return: Dictionary of the number of messages in each queue
    """
    client = boto3.client('sqs')
    queues = ['TRACK_QUEUE', 'VIDEO_QUEUE', 'DEAD_QUEUE']
    processor = resources['PROCESSOR']
    num_messages_visible = {}
    num_messages_invisible = {}
    for q in queues:
        response = client.get_queue_attributes(
            QueueUrl=resources[q],
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'])
        num_messages_visible[q] = response['Attributes']['ApproximateNumberOfMessages']
        num_messages_invisible[q] = response['Attributes']['ApproximateNumberOfMessagesNotVisible']
        if q == 'TRACK_QUEUE':
            info(f'{processor}:{q} number of completed videos: {response["Attributes"]["ApproximateNumberOfMessages"]}')

            # fetch the last 10 messages
            response = client.receive_message(
                QueueUrl=resources[q],
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All'],
                VisibilityTimeout=0,
                WaitTimeSeconds=0)
            if 'Messages' in response:
                for m in response['Messages']:
                    message = parse_message(m)
                    # get the video name which is the video id split from the .tracks.tar.gz
                    # assume this is a mp4 video
                    video = Path(message['video']).name.split('.tracks.tar.gz')[0] + '.mp4'
                    JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                    JobCache().set_media(message['job'], video, JobStatus.SUCCESS, message['timestamp'])

        if q == 'VIDEO_QUEUE':
            info(
                f'{processor}:{q} number of videos to process: {response["Attributes"]["ApproximateNumberOfMessages"]} ' \
                f' number of videos in progress: {response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')

            # fetch the last 10 messages
            response = client.receive_message(
                QueueUrl=resources[q],
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All'],
                VisibilityTimeout=0,
                WaitTimeSeconds=0)
            if 'Messages' in response:
                for m in response['Messages']:
                    message = parse_message(m)
                    video = Path(message['video']).name.split('.tracks.tar.gz')[0] + '.mp4'
                    JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                    JobCache().set_media(message['job'], video, JobStatus.QUEUED, message['timestamp'])

        if q == 'DEAD_QUEUE':
            info(f'{processor}:{q} number of failed videos: {response["Attributes"]["ApproximateNumberOfMessages"]}')

            # fetch the last 10 messages
            response = client.receive_message(
                QueueUrl=resources[q],
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All'],
                VisibilityTimeout=0,
                WaitTimeSeconds=0)
            if 'Messages' in response:
                for m in response['Messages']:
                    message = parse_message(m, True)
                    video = Path(message['video']).name
                    JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                    JobCache().set_media(message['job'], video, JobStatus.FAIL, message['timestamp'])

    return num_messages_visible


def receive_messages(queue, max_number, wait_time):
    """
    Receive a batch of messages in a single request from an SQS queue.

    :param queue: The queue from which to receive messages.
    :param max_number: The maximum number of messages to receive. The actual number
                       of messages received might be less.
    :param wait_time: The maximum time to wait (in seconds) before returning. When
                      this number is greater than zero, long polling is used. This
                      can result in reduced costs and fewer false empty responses.
    :return: The list of Message objects received. These each contain the body
             of the message and metadata and custom attributes.
    """
    try:
        messages = queue.receive_messages(
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=max_number,
            WaitTimeSeconds=wait_time
        )
        for msg in messages:
            debug(f"Received message: {msg.message_id}: {msg.body}")
    except ClientError as error:
        exception(f"Couldn't receive messages from queue: {queue}")
        raise error
    else:
        return messages


# Create a new single threaded executor to run the monitor and update the status
# of the job

class Monitor(Thread):
    def __init__(self, job_description: str, resources: dict, update_period: int = 60, report_update_period: int = 60):
        Thread.__init__(self)
        self.resources = resources
        self.update_period = update_period
        self.report_update_period = report_update_period
        # reporting report_update_period must be >= update_period
        if self.report_update_period < self.update_period:
            warn(f'report_update_period must be >= update_period. Setting report_update_period to {self.update_period}')
            self.report_update_period = self.update_period

        # Get the number of videos to process from the job description
        media = JobCache().get_all_media_names(job_description)
        self.num_videos = len(media)
        self.job_name = job_description

    def run(self):
        while True:
            if self.num_videos == 0:
                warn(f'No videos to process. Stopping monitor.')
                break

            num_activities = log_scaling_activities(self.resources, num_records=10)
            queue_dict = log_queue_status(self.resources)
            queue_activity = sum([int(i) for i in queue_dict.values()])

            if num_activities > 0 or queue_activity:

                # get the number of completed videos
                num_found = JobCache().get_num_completed(self.job_name)

                # get the number of failed videos
                num_failed = JobCache().get_num_failed(self.job_name)

                # if the total completed videos plus the number of failed videos equals the number
                # of videos to process, then stop monitoring
                if num_found + num_failed == self.num_videos:
                    info(f'All videos processed. Stopping monitor.')

                    # if there are failed videos, then set the job status to failed
                    if num_failed > 0:
                        JobCache().set_job(self.job_name, self.resources['CLUSTER'], [], JobStatus.FAIL)
                    else:
                        JobCache().set_job(self.job_name, self.resources['CLUSTER'], [], JobStatus.SUCCESS)
                    break

                else:
                    info(f'Found {num_found} completed videos and {num_failed} failed videos. ')

                # generate a report every report_update_period
                if num_found % self.report_update_period == 0:
                    JobCache().create_report(self.job_name, Path('reports'))

            else:
                # if there is no activity, then stop monitoring
                info(f'No activity for {self.resources["PROCESSOR"]}. Stopping monitor.')
                break

            # if there is activity, then continue to monitor
            time.sleep(self.interval)

        # generate a report
        JobCache().create_report(self.job_name, Path('reports'))
