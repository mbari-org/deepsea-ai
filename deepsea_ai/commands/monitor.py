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

from deepsea_ai.database.job.misc import Status
from deepsea_ai.database.report_generator import create_report
from deepsea_ai.logger import info, warn, debug, exception, err
from deepsea_ai.database.job.database import Job
from deepsea_ai.database.job.database_helper import get_num_completed, get_num_failed, update_media


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
    Logs the status of the queues
    :param resources: Dictionary of resources
    :return: Dictionary of the number of messages in each queue
    """
    client = boto3.client('sqs')
    queues = ['TRACK_QUEUE', 'VIDEO_QUEUE', 'DEAD_QUEUE']
    processor = resources['PROCESSOR']
    num_messages_visible = {}
    num_messages_invisible = {}

    def update_job(sqs_message:dict, video_name: str, status: str):
        """Helper function to update the media status in a given job in the database"""
        job = Job.query.filter_by(name=sqs_message['job'], cluster=resources['CLUSTER']).first()

        if job is None:
            err(f'Job {message["job"]} not found in database.')
            return
        else:
            update_media(db, job, video_name, status)
            info(f"Updated job {job.name} running on {resources['CLUSTER']} in cache. {video_name} {status}")

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
                    response = queue.receive_messages(MaxNumberOfMessages=10)
                    if 'Messages' in response:
                        messages = response['Messages']
                        for m in messages:
                            message = parse_message(m)
                            # get the video name which is the video id split from the .tracks.tar.gz
                            # assume this is a mp4 video
                            video = Path(message['video']).name.split('.tracks.tar.gz')[0] + '.mp4'
                            update_job(message, video, Status.SUCCESS)
                    else:
                        break

            if q == 'VIDEO_QUEUE':
                info(
                    f'{processor}:{q} number of videos to process: {response["Attributes"]["ApproximateNumberOfMessages"]} ' \
                    f' number of videos in progress: {response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')
                # fetch all the messages
                while True:
                    response = queue.receive_messages(MaxNumberOfMessages=10)
                    if 'Messages' in response:
                        messages = response['Messages']
                        for m in messages:
                            message = parse_message(m)
                            video = Path(message['video']).name
                            update_job(message, video, Status.QUEUED)
                    else:
                        break

            if q == 'DEAD_QUEUE':
                info(
                    f'{processor}:{q} number of failed videos: {response["Attributes"]["ApproximateNumberOfMessages"]}')

                # fetch all the messages
                while True:
                    response = queue.receive_messages(MaxNumberOfMessages=10)
                    if 'Messages' in response:
                        messages = response['Messages']
                        for m in messages:
                            message = parse_message(m)
                            video = Path(message['video']).name
                            update_job(message, video, Status.FAILED)
                    else:
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
    def __init__(self, resources: dict, update_period: int = default_update_period, sim: bool = False):
        Thread.__init__(self)
        self.resources = resources
        self.update_period = update_period
        self.sim = sim

        # reporting update_period must be >= update_period
        if self.update_period < self.update_period:
            warn(f'update_period must be >= update_period. Setting update_period to {self.update_period}')
            self.update_period = self.update_period

    def check_job_status(self, job: Job) -> (int, int):
        """
        Check the status of the job
        :param job: Job to check
        :return: Number of completed videos, number of failed videos
        """

        # get the number of completed videos
        num_found = get_num_completed(job)

        # get the number of failed videos
        num_failed = get_num_failed(job)

        f'Job {job}: Found {num_found} completed videos and {num_failed} failed videos.'
        return num_found, num_failed

    def run(self):
        init = True
        if self.sim:
            return

        while True:
            # check the status of the job in the database
            job = db.query(Job).filter(Job.name == self.name).first()
            if job is None:
                err(f'Job {self.name} not found in database. Cannot monitor. Trying again in {self.update_period} seconds.')

            num_activities = log_scaling_activities(self.resources, num_records=10)
            queue_dict = log_queue_status(self.resources)
            queue_activity = sum([int(i) for i in queue_dict.values()])

            if num_activities == 0 and queue_activity == 0:
                info(f'No activity for {self.resources["PROCESSOR"]}.')
            else:
                # generate a report every update_period, or if we are just starting
                if self.update_period == 0 or init:
                    info(f"Getting jobs for cluster {self.resources['CLUSTER']}")
                    jobs = db.query(Job).filter(Job.cluster == self.resources['CLUSTER']).all()
                    info(f"Found {len(jobs)} jobs for cluster {self.resources['CLUSTER']}")
                    for job in jobs:
                        create_report(job, Path('reports'), self.resources)
                        init = False

            info(f'Checking again in {self.update_period} seconds. Ctrl-C to stop.')
            time.sleep(self.update_period)

        # generate a report
        job = db.query(Job).filter(Job.name == self.name).first()
        if job is None:
            err(f'Job {self.name} not found in database.')
        else:
            create_report(job, Path('reports'), self.resources)
