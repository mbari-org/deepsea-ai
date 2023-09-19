# deepsea-ai, Apache-2.0 license
# Filename: commands/process.py
# Description: Process a collection of videos with the SageMaker ScriptProcessor

import os
import inspect
import uuid

import boto3
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from deepsea_ai.config import config as cfg
from deepsea_ai.commands.upload_tag import get_prefix
from deepsea_ai.database.job.database import Job, Media, PydanticJobWithMedias
from deepsea_ai.database.job.database_helper import update_media, json_b64_encode
from deepsea_ai.database.job.misc import Status, JobType
from deepsea_ai.logger import debug, info, err

from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

code_path = Path(os.path.abspath(inspect.getfile(inspect.currentframe())))


def script_processor_run(session_maker: sessionmaker, dry_run: bool, input_s3: tuple, output_s3: tuple, model_s3: tuple,
                         volume_size_gb: int, instance_type: str, custom_config: cfg.Config,
                         tags: dict, config_s3: str, args: str):
    """
    Process a collection of videos with the ScriptProcessor
    """
    user_name = "SIM" if dry_run else custom_config.get_username()

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
    account = "00000" if dry_run else custom_config.get_account()
    region = "us-west-2" if dry_run else custom_config.get_region()
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
    job_name = f"{base_job_name}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    info(f"Job name: {job_name}")

    def log_fini(db: Session, j: Job, status: str, **kwargs):
        j_p = PydanticJobWithMedias.from_orm(j)
        for m in j_p.media:
            update_media(db, j, m.name, status, **kwargs)

    if not dry_run:
        # get a list of videos in the input bucket
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(input_s3.netloc)
        videos = [obj.key for obj in bucket.objects.filter(Prefix=input_s3.path.lstrip('/'))]
        debug(f'Found videos {videos}')

        # Don't continue if there are no videos
        if len(videos) == 0:
            msg = f"No videos found in s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}"
            err(msg)
            return

        video_names = [Path(v).name for v in videos]

        # Add the job to the database and set the status to QUEUED for each video
        job = Job(engine=processor,
                  name=job_name,
                  job_type=JobType.SAGEMAKER)

        for name in video_names:
            m = Media(name=name,
                      status=Status.QUEUED,
                      updatedAt=datetime.now(),
                      job=job,
                      metadata_b64=json_b64_encode({
                          'image_uri_ecr': image_uri_ecr,
                          'instance_type': instance_type,
                          'volume_size_in_gb': volume_size_gb,
                          'max_runtime_in_seconds': 172800,
                          'tags': tags,
                          'arguments': arguments,
                          'processing_job_arn': '',
                          'error': ''
                      }))
            job.media.append(m)

        with session_maker.begin() as db:
            db.add(job)

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
        with session_maker.begin() as db:
            job = db.query(Job).filter(Job.name == job_name).first()
            if script_processor.jobs[-1].describe()['ProcessingJobStatus'] == 'Failed':
                reason = script_processor.jobs[-1].describe()['FailureReason']
                msg = f"Script processor failed for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}: {reason}"
                log_fini(db, job, Status.FAILED, processing_job_arn=script_processor.jobs[-1].job_name, error=reason)
                err(msg)
                raise Exception(msg)
            else:
                debug(f"Script processor succeeded for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")
                log_fini(db, job, Status.SUCCESS, processing_job_arn=script_processor.jobs[-1].job_name)
    else:
        debug(f"Script processor dry run for inputs s3://{input_s3.netloc}/{input_s3.path.lstrip('/')}")


def batch_run(session_maker: sessionmaker, resources: dict, video_path: Path, job_name: str, user_name: str, clean: bool, args: str):
    """
    Process a collection of videos in with a cluster in the Elastic Container Service [ECS]
    """
    # the queue to submit the processing message to
    queue_name = resources['VIDEO_QUEUE']

    # Get the service resource
    sqs = boto3.resource('sqs')

    prefix_path = get_prefix(video_path)

    # Setup message dict
    # Generate a unique uuid to track the video processing
    message_uuid = str(uuid.uuid4())
    message_dict = {"video": f"{prefix_path}/{video_path.name}",
                    "clean": "True" if clean else "False",
                    "user_name": user_name,
                    "metadata_b64": json_b64_encode({"message_uuid": message_uuid}),
                    "job_name": job_name}

    # If args are provided, add them to the message dict
    if args:
        # Strip off the quotes
        args = args.strip('"')
        message_dict["args"] = args

    queue = sqs.get_queue_by_name(QueueName=queue_name)
    json_object = json.dumps(message_dict, indent=4)

    # Create a message group based on the time and the video name
    group_id = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{video_path.name}"

    # Create a new message
    response = queue.send_message(MessageBody=json_object, MessageGroupId=group_id)
    info(f"Message queued to {queue_name}. MessageId: {response.get('MessageId')}")

    with session_maker.begin() as db:
        # Add the job to the database if it doesn't exist
        job = db.query(Job).filter(Job.name == job_name).first()
        try:
            if job is None:
                job = Job(engine=resources['CLUSTER'],
                          name=job_name,
                          job_type=JobType.ECS)
                db.add(job)
        except Exception as ex:
            err(f"Failed to add job {job_name} to cache: {ex}")
            raise ex

    with session_maker.begin() as db:
        job = db.query(Job).filter(Job.name == job_name).first()
        info(f"Added job {job.name} running on {resources['CLUSTER']} to cache.")
        update_media(db, job, f"{prefix_path}/{video_path.name}", Status.QUEUED, message_uuid=message_uuid)