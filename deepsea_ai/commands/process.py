# !/usr/bin/env python
__author__ = "Danelle Cline, Duane Edgington"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Process a collection of videos; assumes videos have previously been uploaded with the upload command

@author: __author__
@status: __status__
@license: __license__
'''

import os
import inspect
import boto3
import json
from datetime import datetime
from pathlib import Path

from deepsea_ai.config import config as cfg
from deepsea_ai.commands.upload_tag import get_prefix
from deepsea_ai.logger import debug, info, err, warn, exception, keys
from deepsea_ai.logger.job_cache import JobStatus, JobCache

from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

code_path = Path(os.path.abspath(inspect.getfile(inspect.currentframe())))

def script_processor_run(dry_run: bool, input_s3: tuple, output_s3: tuple, model_s3: tuple,
                         volume_size_gb: int, instance_type: str, custom_config: cfg.Config,
                         tags: dict, config_s3: str, args: str):
    """
    Process a collection of videos with the ScriptProcessor
    """
    user_name = custom_config.get_username()

    arguments = ['dettrack', f"--model-s3=s3://{model_s3.netloc}/{model_s3.path.lstrip('/')}"]
    if args:
        # args needs to be quoted
        args_quoted = f'"{args}"'
        arguments.append(f'--args={args_quoted}')

    if config_s3:
        arguments.append(f'--config-s3={config_s3}')

    info(f'Running with args {arguments}')

    # Construct the uri from the config, e.g.
    # mbari/deepsea-yolov5:1.1.2 => 872338704006.dkr.ecr.us-west-2.amazonaws.com/deepsea-yolov5:1.1.2
    account = custom_config.get_account()
    region = custom_config.get_region()
    image_uri_docker = custom_config('docker', 'strongsort_container')
    image_uri_ecr = f"{account}.dkr.ecr.{region}.amazonaws.com/{image_uri_docker}"
    # log the video as running; the processor is the docker image
    processor = image_uri_ecr.split('/')[-1]
    base_job_name = f'strongsort-yolov5-{user_name}'

    script_processor = ScriptProcessor(command=['python3'],
                                       image_uri=image_uri_ecr,
                                       role=custom_config.get_role(),
                                       instance_count=1,
                                       base_job_name=base_job_name,
                                       instance_type=instance_type,
                                       volume_size_in_gb=volume_size_gb,
                                       max_runtime_in_seconds=172800,
                                       tags=tags)

    # log it
    info(f"Start script processor for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")

    videos = []

    if not dry_run:
        # get a list of videos in the input bucket
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(input_s3.netloc)
        videos = [obj.key for obj in bucket.objects.filter(Prefix=input_s3.path.lstrip('/'))]
        debug(videos)

        # Don't continue if there are no videos
        if len(videos) == 0:
            msg = f"No videos found in s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}"
            err(msg)
            return

        # strip off the prefix
        videos = [video.replace(input_s3.path.lstrip('/'), '') for video in videos]

        JobCache().set_job(base_job_name, processor, videos, JobStatus.RUNNING)
        for v in videos:
            JobCache().set_media(base_job_name, v, JobStatus.RUNNING)

        # run the script processor
        script_processor.run(code=f'{code_path.parent.parent.parent}/deepsea_ai/pipeline/run_strongsort.py',
                             arguments=arguments,
                             inputs=[ProcessingInput(
                                 source=f"s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}",
                                 destination='/opt/ml/processing/input')],
                             outputs=[ProcessingOutput(source='/opt/ml/processing/output',
                                                       destination=f"s3://{output_s3.netloc}/{output_s3.path.lstrip('/')}")]
                             )

        # log success/failure
        if script_processor.jobs[-1].describe()['ProcessingJobStatus'] == 'Failed':
            reason = script_processor.jobs[-1].describe()['FailureReason']
            msg = f"Script processor failed for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}: {reason}"
            JobCache().set_job(base_job_name, processor, videos, JobStatus.FAILED)
            for v in videos:
                JobCache().set_media(base_job_name, v, JobStatus.FAILED)
            err(msg)
            raise Exception(msg)
        else:
            debug(f"Script processor succeeded for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
            JobCache().set_job(base_job_name, processor, videos, JobStatus.SUCCESS)
            for v in videos:
                JobCache().set_media(base_job_name, v, JobStatus.SUCCESS)
    else:
        debug(f"Script processor dry run for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
        JobCache().set_job(base_job_name, processor, videos, JobStatus.SUCCESS)
        for v in videos:
            JobCache().set_media(base_job_name, v, JobStatus.SUCCESS)


def batch_run(resources: dict, video_path: Path, job_name: str, user_name: str, clean: bool, args: str):
    """
    Process a collection of videos in with a cluster in the Elastic Container Service [ECS]
    """
    # the queue to submit the processing message to
    queue_name = resources['VIDEO_QUEUE']

    # Get the service resource
    sqs = boto3.resource('sqs')

    prefix_path = get_prefix(video_path)

    # Setup message dict
    message_dict = {"video": f"{prefix_path}/{video_path.name}",
                    "clean": "True" if clean else "False",
                    "user_name": user_name,
                    "job_name": job_name}

    # If args are provided, add them to the message dict
    if args:
        message_dict["args"] = args

    queue = sqs.get_queue_by_name(QueueName=queue_name)
    json_object = json.dumps(message_dict, indent=4)

    now = datetime.utcnow()

    # create a message group based on the time and the job_name to avoid collisions
    group_id = now.strftime('%Y%m%dT%H%M')

    # create a new message
    response = queue.send_message(MessageBody=json_object, MessageGroupId=resources['CLUSTER'] + f"{group_id}")
    info(f"Message queued to {queue_name}. MessageId: {response.get('MessageId')}")

    # log the video to the job cache
    JobCache().set_job(job_name, resources['CLUSTER'], [video_path.name], JobStatus.QUEUED)
    JobCache().set_media(job_name, video_path.name, JobStatus.QUEUED)
