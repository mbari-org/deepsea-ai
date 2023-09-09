# deepsea-ai, Apache-2.0 license
# Filename: commands/monitor_utils.py
# Description: Helper commands to monitor the status of tasks run on an ECS cluster.

import json
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from deepsea_ai.database.job import Job, Status
from deepsea_ai.database.job.database_helper import update_media
from deepsea_ai.logger import info, err, exception, debug


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


def parse_message(message: dict) -> dict:
    """
    Parse the JSON formated message from the queue body
    :param message: Message from the queue
    :return: Dictionary of the message with video, job, and timestamp or None if the message is invalid
    """
    try:
        if 'Body' not in message:
            err(f'No body in message {message}')
            return None
        b = json.loads(message['Body'])
        utc_secs = int(message['Attributes']['ApproximateFirstReceiveTimestamp'])
        timestamp = datetime.utcfromtimestamp(utc_secs / 1000)
        b['timestamp'] = timestamp.strftime('%Y%m%dT%H%M%S')
        # add the message id to the message if it does not exist; it is used to update the database
        # if 'message_id' not in b:
        #     b['message_id'] = message['MessageId']
        return b
    except Exception as e:
        exception(e)
        return None


def fetch_and_parse(client, q):
    """
    Fetch queues with long polling
    Can only fetch 10 messages at a time; wait up to 20 seconds for a message
    :param client: the sqs client
    :param q: The queue to fetch messages from
    :return: List of parsed messages from the queue
    """
    messages = []
    response = client.receive_message(QueueUrl=q,
                                      MaxNumberOfMessages=10,
                                      VisibilityTimeout=5, # Fetch both visible and invisible messages
                                      WaitTimeSeconds=20,
                                      MessageAttributeNames=['All'],
                                      AttributeNames=['All'])
    if 'Messages' in response:
        for m in response['Messages']:
            message = parse_message(m)
            if message:
                messages.append(message)

    return messages


def log_queue_status(db: Session, resources: dict) -> dict:
    """
    Logs the status of the queues
    :param resources: Dictionary of resources
    :return: Dictionary of the number of messages in each queue
    :param db: The database session
    :param resources: Dictionary of resources in the cluster
    :return: Dictionary of the number of messages visible in each queue
    """
    client = boto3.client('sqs')
    queues = ['TRACK_QUEUE', 'VIDEO_QUEUE', 'DEAD_QUEUE']
    processor = resources['PROCESSOR']
    num_messages_visible = {}
    num_messages_invisible = {}

    def update_job(sqs_message: dict, video_name: str, status: str):
        """
        Helper function to update the database
        :param sqs_message: The message from the queue
        :param video_name: The name of the video
        :param status: The status of the video, either QUEUED, SUCCESS, or FAILED
        """
        job = db.query(Job).filter_by(name=sqs_message['job_name'], engine=resources['CLUSTER']).first()

        if job is None:
            err(f'Job {message["job_name"]} not found in database.')
            # Add the job to the database
            job = Job(name=sqs_message['job_name'], engine=resources['CLUSTER'], job_type='ECS')
            db.add(job)
            db.commit()

        update_media(db, job, video_name, status)
        info(f"Updated job {job.name} running on {resources['CLUSTER']} in cache. {video_name} {status}")

    try:
        for q in queues:
            response = client.get_queue_attributes(
                QueueUrl=resources[q],
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'])
            num_messages_visible[q] = response['Attributes']['ApproximateNumberOfMessages']
            num_messages_invisible[q] = response['Attributes']['ApproximateNumberOfMessagesNotVisible']

            if q == 'TRACK_QUEUE':
                info(f'{processor}:{q} number of processed videos: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]}')
                messages = fetch_and_parse(client, resources[q])
                for message in messages:
                    # get the video name which is the video id split from the .tracks.tar.gz
                    # assume this is a mp4 video
                    video = Path(message['video']).name.split('.tracks.tar.gz')[0] + '.mp4'
                    update_job(message, video, Status.SUCCESS)

            if q == 'VIDEO_QUEUE':
                info(f'{processor}:{q} number of videos to process: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]} ')
                info(f' number of videos in progress: '
                     f'{response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')

                messages = fetch_and_parse(client, resources[q])
                for message in messages:
                    video = Path(message['video']).name
                    update_job(message, video, Status.QUEUED)

            if q == 'DEAD_QUEUE':
                info(f'{processor}:{q} number of failed videos: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]}')
                messages = fetch_and_parse(client, resources[q])
                for message in messages:
                    video = Path(message['video']).name
                    update_job(message, video, Status.FAILED)

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
