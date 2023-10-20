# deepsea-ai, Apache-2.0 license
# Filename: commands/monitor_utils.py
# Description: Helper commands to monitor the status of tasks run on an ECS cluster.

import json
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session, sessionmaker

from deepsea_ai.database.job import Job, Status
from deepsea_ai.database.job.database_helper import update_media, json_b64_decode
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
    :return: Dictionary of the message with the timestamp added
    """
    try:
        if 'Body' not in message:
            err(f'No body in message {message}')
            return None
        b = json.loads(message['Body'])
        utc_secs = int(message['Attributes']['ApproximateFirstReceiveTimestamp'])
        timestamp = datetime.utcfromtimestamp(utc_secs / 1000)
        b['timestamp'] = timestamp.strftime('%Y%m%dT%H%M%S')
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
    while True:
        response = client.receive_message(QueueUrl=q,
                                          MaxNumberOfMessages=10,
                                          WaitTimeSeconds=20,
                                          MessageAttributeNames=['All'],
                                          AttributeNames=['All'])
        if 'Messages' not in response:
            break

        for m in response['Messages']:
            message = parse_message(m)
            if message:
                messages.append(message)

    return messages


def update_job(db: Session, sqs_message: dict, cluster: str, status: str):
    """
    Helper function to update the database
    :param db: Database session
    :param sqs_message: The message from the queue
    :param cluster: The cluster the job is running on
    :param status: The status of the video, either QUEUED, SUCCESS, or FAILED
    """
    job = db.query(Job).filter_by(name=sqs_message['job_name'], engine=cluster).first()

    if job is None:
        err(f'Job {sqs_message["job_name"]} not found in database.')
        # Add the job to the database
        job = Job(name=sqs_message['job_name'], engine=cluster, job_type='ECS')
        db.add(job)
    else:
        info(f'Found job {job.name} running on {cluster} in cache.')

    # pass through the metadata
    update_media(db, job, sqs_message["video"], status, metadata_b64=sqs_message['metadata_b64'])


def log_queue_status(session_maker: sessionmaker, resources: dict) -> dict:
    """
    Logs the status of the queues
    :param resources: Dictionary of resources
    :return: Dictionary of the number of messages in each queue
    :param resources: Dictionary of resources in the cluster
    :return: Dictionary of the number of messages visible in each queue
    """
    client = boto3.client('sqs')
    queues = ['VIDEO_QUEUE', 'TRACK_QUEUE', 'DEAD_QUEUE']
    cluster = resources['CLUSTER']
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

            if q == 'TRACK_QUEUE':
                info(f'{processor}:{q} number of processed videos: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]}')
                messages = fetch_and_parse(client, resources[q])
                if messages:
                    with session_maker() as db:
                        for message in messages:
                            update_job(db, message, cluster, Status.SUCCESS)

            if q == 'VIDEO_QUEUE':
                info(f'{processor}:{q} number of videos to process: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]} ')
                info(f' number of videos in progress: '
                     f'{response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]}')

                # This needs to be tested in a multiple user scenario
                # For now, assume single user, single command execution use-case only
                # messages = fetch_and_parse(client, resources[q])
                # if messages:
                #     with session_maker() as db:
                #         for message in messages:
                #             update_job(db, message, cluster, Status.QUEUED)

            if q == 'DEAD_QUEUE':
                info(f'{processor}:{q} number of failed videos: '
                     f'{response["Attributes"]["ApproximateNumberOfMessages"]}')
                messages = fetch_and_parse(client, resources[q])
                if messages:
                    with session_maker() as db:
                        for message in messages:
                            update_job(db, message, cluster, Status.FAILED)

    except ClientError as e:
        exception(e)
        raise e

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
