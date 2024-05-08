# deepsea-ai, Apache-2.0 license
# Filename: commands/ecsshutdown.py
# Description: ECS cluster shutdown

import boto3
import time
import json
from deepsea_ai.config.config import Config
from deepsea_ai.logger import info, debug, err, create_logger_file


def ecsshutdown(resources: dict, cluster: str):
    """
     Shutdown the ECS cluster. This function stops all running services, tasks, and container instances in the ECS cluster.
     Any completed video track results are also removed from S3 and auto-scaling is disabled for the ECS service
     temporarily to prevent new tasks from starting for 5 minutes.
    """
    autoscaling = boto3.client('autoscaling')
    sqs = boto3.client('sqs')
    s3 = boto3.client('s3')
    ecs = boto3.client('ecs')

    # Get the cluster arn
    response = ecs.list_clusters()
    for c in response['clusterArns']:
        print(c)
        if cluster in c:
            cluster_arn = c
            info(f"Found cluster {cluster} ARN {cluster_arn}")
            break

    if cluster_arn is None:
        err(f"Cluster {cluster} not found")
        return

    # Stop the auto-scaling of the ECS service
    response = ecs.describe_capacity_providers()
    capacity_providers = response['capacityProviders']

    # Stop the auto-scaling of the ECS service by disabling the capacity provider
    for cp in capacity_providers:
        if cp['name'].split('-')[0] == cluster:
            autoScalingGroupName = cp['autoScalingGroupProvider']['autoScalingGroupArn'].split('/')[-1]
            # Capture the max size of the capacity provider to reset it later
            asg = autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[autoScalingGroupName]
            )
            max_size = max(asg['AutoScalingGroups'][0]['MaxSize'], 6)
            response = autoscaling.update_auto_scaling_group(
                AutoScalingGroupName=autoScalingGroupName,
                MinSize=0,
                MaxSize=0,
            )
            debug(response)
            info(f"Autoscaling disabled for capacity provider {cp['name']}")
            break

    # Stop any running services in the cluster
    response = ecs.list_services(cluster=cluster_arn)
    services = response['serviceArns']
    for service in services:
        response = ecs.update_service(
            cluster=cluster_arn,
            service=service,
            desiredCount=0
        )
        info(f"Stopped service {service}")

    # Stop any container instances in the cluster
    response = ecs.list_container_instances(cluster=cluster_arn)
    container_instances = response['containerInstanceArns']
    for container_instance in container_instances:
        response = ecs.update_container_instances_state(
            cluster=cluster_arn,
            containerInstances=[container_instance],
            status='DRAINING'
        )
        info(f"Stopped container instance {container_instance}")

    # Stop any running tasks in the cluster
    response = ecs.list_tasks(cluster=cluster_arn)
    tasks = response['taskArns']
    for task in tasks:
        response = ecs.stop_task(cluster=cluster_arn, task=task)
        debug(response)
        info(f"Stopped task {task}")

    # Get the messages in the TRACK_QUEUE and delete them
    # These are completed video track messages, so capture the locations of the completed track files and
    # remove the track results from S3
    def receive_track_messages():
        response = sqs.receive_message(QueueUrl=resources['TRACK_QUEUE'],
                                       AttributeNames=['All'],
                                       MessageAttributeNames=['All'])

        if 'Messages' in response:
            messages = response['Messages']
            print(f"Received {len(messages)} messages from {resources['TRACK_QUEUE']}")

            for message in messages:
                debug(f"Message ID: {message['MessageId']}")
                debug(f"Message Body: {message['Body']}")
                debug(f"Message Attributes: {message.get('MessageAttributes', '')}")
                debug("--------------------")
                message_body = message['Body']
                message_dict = json.loads(message_body)
                if message_dict['status'] == 'SUCCESS':
                    # Get the track file location and remove the file from S3
                    track_file = message_dict['results']
                    info(f"Removing track file {track_file}")
                    s3.delete_object(Bucket=resources['TRACK_BUCKET'], Key=track_file)
                # Update the message with messageId as FAILED, send to DEAD_QUEUE and delete from TRACK_QUEUE
                message_dict['status'] = 'FAILED'
                sqs.send_message(QueueUrl=resources['DEAD_QUEUE'],
                                 MessageBody=json.dumps(message_dict, indent=4),
                                 MessageGroupId=message['Attributes']['MessageGroupId'])
                sqs.delete_message(QueueUrl=resources['TRACK_QUEUE'],
                                   ReceiptHandle=message['ReceiptHandle'])
        else:
            info(f"No messages available in {resources['TRACK_QUEUE']}. Track clean-up and shutdown complete")

        # If there are more messages, continue to receive
        if 'Messages' in response and len(response['Messages']) == 10:
            receive_track_messages()

    receive_track_messages()

    def receive_video_messages():
        response = sqs.receive_message(QueueUrl=resources['VIDEO_QUEUE'],
                                       AttributeNames=['All'],
                                       MessageAttributeNames=['All'])

        if 'Messages' in response:
            messages = response['Messages']
            print(f"Received {len(messages)} messages")

            for message in messages:
                # on failure push this message to the dead letter queue
                message_body = message['Body']
                message_body = json.loads(message_body)
                message_body["error"] = "ECS cluster shutdown"
                message_body["status"] = "FAILED"
                print(f'Sending message {message} to dead queue {resources["DEAD_QUEUE"]}')
                response = sqs.send_message(QueueUrl=resources['DEAD_QUEUE'],
                                                 MessageBody=json.dumps(message_body, indent=4),
                                                 MessageGroupId=message['Attributes']['MessageGroupId'])
                debug(response)
                response = sqs.send_message(QueueUrl=resources['DEAD_QUEUE'],
                                 MessageBody=json.dumps(message_body),
                                 MessageGroupId=message['Attributes']['MessageGroupId'])
                debug(response)
            else:
                info(f"No messages available in {resources['VIDEO_QUEUE']}."
                     f"No videos were being processed during shutdown.")

    receive_video_messages()

    info(f'Shutdown of ECS cluster {cluster} complete. Waiting 5 minutes before restarting autoscaling to reenable ')
    time.sleep(300)

    info(f"Restarting autoscaling for capacity provider {cp['name']} to max size {max_size}")
    response = autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=autoScalingGroupName,
        MinSize=0,
        MaxSize=max_size,
    )
    debug(response)
    info(f"Autoscaling enabled. Desired count set to {max_size}.")
    info("ECS cluster shutdown complete for {cluster}")


if __name__ == '__main__':
    from pathlib import Path
    cluster = 'y5x315k'
    create_logger_file(log_path=Path.cwd(), prefix="ecsshutdown")
    default_config = Config()
    resources = default_config.get_resources(cluster)
    ecsshutdown(resources, cluster)
    print(resources)
