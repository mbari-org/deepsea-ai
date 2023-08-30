# deepsea-ai, Apache-2.0 license
# Filename: commands/process.py
# Description: Process a collection of videos with the SageMaker ScriptProcessor

import os
import inspect
import boto3
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from deepsea_ai.config import config as cfg
from deepsea_ai.commands.upload_tag import get_prefix
from deepsea_ai.database.job.database import Job, Media, PydanticJobWithMedias
from deepsea_ai.database.job.database_helper import update_media
from deepsea_ai.database.job.misc import Status, JobType
from deepsea_ai.logger import debug, info, err

from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

code_path = Path(os.path.abspath(inspect.getfile(inspect.currentframe())))


def script_processor_run(db: Session, dry_run: bool, input_s3: tuple, output_s3: tuple, model_s3: tuple,
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

    def log_fini():
        debug(f"Script processor dry run for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
        # Get the job from the database and set the status to SUCCESS for each video
        j = db.query(Job).filter(Job.name == base_job_name).first()
        j_p = PydanticJobWithMedias.from_orm(job)
        for m in j_p.medias:
            update_media(db, j, m.name, Status.SUCCESS)

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

        # Strip off the prefix
        videos = [video.replace(input_s3.path.lstrip('/'), '') for video in videos]

        # Add the job to the database
        name = base_job_name
        job = Job(cluster=processor, name=name, job_type=JobType.SAGEMAKER)
        db.add(job)

        for v in videos:
            m = Media(name=v, status=Status.QUEUED, updatedAt=datetime.now(), job=job)
            db.add(m)
        db.commit()

        # Run the script processor
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

            # Get the job from the database and set the status to FAILED for each video
            job = db.query(Job).filter(Job.name == base_job_name).first()
            for v in videos:
                update_media(db, job, v, Status.FAILED)

            err(msg)
            raise Exception(msg)
        else:
            debug(f"Script processor succeeded for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
            log_fini()
    else:
        debug(f"Script processor dry run for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
        log_fini()


def batch_run(db: Session, resources: dict, video_path: Path, job_name: str, user_name: str, clean: bool, args: str):
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
        # Strip off the quotes
        args = args.strip('"')
        message_dict["args"] = args

    queue = sqs.get_queue_by_name(QueueName=queue_name)
    json_object = json.dumps(message_dict, indent=4)

    now = datetime.utcnow()

    # Create a message group based on the time and the video name
    group_id = f"{now.strftime('%Y%m%dT%H%M%S')}-{video_path.name}"

    # Create a new message
    response = queue.send_message(MessageBody=json_object, MessageGroupId=resources['CLUSTER'] + f"{group_id}")
    info(f"Message queued to {queue_name}. MessageId: {response.get('MessageId')}")

    # Add the job to the database if it doesn't exist
    job = db.query(Job).filter(Job.name == job_name).first()
    try:
        if job is None:
            job = Job(name=job_name, cluster=resources['CLUSTER'])
            db.add(job)
            db.commit()
            info(f"Added job {job.name} running on {resources['CLUSTER']} to cache.")

        update_media(db, job, video_path.name, Status.RUNNING)
    except Exception as ex:
        err(f"Failed to add job {job_name} to cache: {ex}")
        raise ex
