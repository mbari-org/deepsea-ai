# deepsea-ai, Apache-2.0 license
# Filename: commands/monitor.py
# Description: Various commands for monitoring the status of processing or training jobs in SQS queues
# that are being consumed by an ECS cluster.

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
    try:
        for q in queues:
            response = client.get_queue_attributes(
                QueueUrl=resources[q],
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'])
            num_messages_visible[q] = response['Attributes']['ApproximateNumberOfMessages']
            num_messages_invisible[q] = response['Attributes']['ApproximateNumberOfMessagesNotVisible']
            sqs = boto3.resource('sqs')
            queue = sqs.Queue(resources[q])
            if q == 'TRACK_QUEUE':
                info(
                    f'{processor}:{q} number of completed videos: {response["Attributes"]["ApproximateNumberOfMessages"]}')
                info(
                    f'{processor}:{q} number of completed videos: {response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')

                # fetch all the messages
                while True:
                    for response in queue.receive_messages(MaxNumberOfMessages=10):
                        if response and 'Messages' in response and len(response['Messages']) > 0:
                            for m in response['Messages']:
                                message = parse_message(m)
                                # get the video name which is the video id split from the .tracks.tar.gz
                                # assume this is a mp4 video
                                video = Path(message['video']).name.split('.tracks.tar.gz')[0] + '.mp4'
                                JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                                JobCache().set_media(message['job'], video, JobStatus.SUCCESS, message['timestamp'])
                        else:
                            break
                    break

            if q == 'VIDEO_QUEUE':
                info(
                    f'{processor}:{q} number of videos to process: {response["Attributes"]["ApproximateNumberOfMessages"]} ' \
                    f' number of videos in progress: {response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')
                # fetch all the messages
                while True:
                    for response in queue.receive_messages(MaxNumberOfMessages=10):
                        if response and 'Messages' in response and len(response['Messages']) > 0:
                            for m in response['Messages']:
                                message = parse_message(m)
                                video = Path(message['video']).name
                                JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                                JobCache().set_media(message['job'], video, JobStatus.QUEUED, message['timestamp'])
                        else:
                            break
                    break

            if q == 'DEAD_QUEUE':
                info(
                    f'{processor}:{q} number of failed videos: {response["Attributes"]["ApproximateNumberOfMessages"]}')

                # fetch all the messages
                while True:
                    for response in queue.receive_messages(MaxNumberOfMessages=10):
                        if response and 'Messages' in response and len(response['Messages']) > 0:
                            for m in response['Messages']:
                                message = parse_message(m)
                                video = Path(message['video']).name
                                JobCache().set_job(message['job'], resources['CLUSTER'], [video], JobStatus.RUNNING)
                                JobCache().set_media(message['job'], video, JobStatus.FAILED, message['timestamp'])
                        else:
                            break
                    break
    except ClientError as e:
        exception(e)
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

default_update_period = 60 * 30  # 30 minutes


class Monitor(Thread):
    def __init__(self, jobs: [str], resources: dict, update_period: int = default_update_period, sim : bool = False):
        Thread.__init__(self)
        self.resources = resources
        self.update_period = update_period
        self.sim = sim
        # reporting update_period must be >= update_period
        if self.update_period < self.update_period:
            warn(f'update_period must be >= update_period. Setting update_period to {self.update_period}')
            self.update_period = self.update_period

        # Get the number of videos to process from the job description
        self.num_videos = 0
        for j in jobs:
            media = JobCache().get_all_media_names(j)
            self.num_videos += len(media)
        self.jobs = jobs

    def check_job_status(self, job):
        # get the number of completed videos
        num_found = JobCache().get_num_completed(job)

        # get the number of failed videos
        num_failed = JobCache().get_num_failed(job)

        # if the total completed videos plus the number of failed videos equals the number
        # of videos to process, then stop monitoring
        if num_found + num_failed == self.num_videos:
            info(f'Job {job} found {num_found} completed videos and {num_failed} failed videos. ')

            # if there are failed videos, then set the job status to failed
            if num_failed > 0:
                JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.FAILED)
            else:
                if num_found == self.num_videos and num_found > 0:
                    JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.SUCCESS)
                else:
                    JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.UNKNOWN)

        else:
            if num_failed > 0:
                JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.FAILED)
                info(
                    f'Job {job}: Found {num_found} completed videos and {num_failed} failed videos.')
            else:
                if num_found == self.num_videos and num_found > 0:
                    JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.SUCCESS)
                else:
                    JobCache().set_job(job, self.resources['CLUSTER'], [], JobStatus.UNKNOWN)
                info(f'Job {job}: found {num_found} completed videos. ')

        return num_found, num_failed

    def run(self):
        init = True
        if self.sim:
            return

        while True:

            num_activities = log_scaling_activities(self.resources, num_records=10)
            queue_dict = log_queue_status(self.resources)
            queue_activity = sum([int(i) for i in queue_dict.values()])

            if num_activities > 0 or queue_activity:

                # check the status of the job
                for j in self.jobs:
                    num_found, num_failed = self.check_job_status(j)

                    # generate a report every update_period, or if we are just starting
                    if num_found % self.update_period == 0 or init:
                        JobCache().create_report(j, Path('reports'), self.resources['PROCESSOR'])

                init = False

            else:
                # if there is no activity, then stop monitoring
                info(f'No activity for {self.resources["PROCESSOR"]}. Stopping monitor.')
                break

            # if there is activity, then continue to monitor
            info(f'Checking again in {self.update_period} seconds. Ctrl-C to stop.')
            time.sleep(self.update_period)

        # generate a report
        for j in self.jobs:
            JobCache().create_report(j, Path('reports'), self.resources['PROCESSOR'])
