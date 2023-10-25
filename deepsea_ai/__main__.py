# deepsea-ai, Apache-2.0 license
# Filename: __main__
# Description: Main entry point for the deepsea_ai command line interface
import time
from datetime import datetime

import boto3
import click
import os
from pathlib import Path
from urllib.parse import urlparse

from deepsea_ai.config.config import Config
from deepsea_ai.commands import upload_tag, process, train, bucket, monitor
from deepsea_ai.config import config as cfg
from deepsea_ai.config import setup
from deepsea_ai.database.job.database import Job, init_db
from deepsea_ai.database.job.misc import JobType
from deepsea_ai import logger
from deepsea_ai.logger import info, err, debug, warn, critical
from deepsea_ai import __version__
from deepsea_ai import common_args

default_config = cfg.Config(quiet=True)
default_config_ini = cfg.default_config_ini
default_report_dir = cfg.default_report_dir
cfg_option = click.option('--config', type=str, default=default_config_ini,
                          help=f'Path to config file to override defaults in {default_config_ini}')


def init(log_prefix: str = "deepsea_ai", config: str = default_config_ini) -> Config:
    python_path = Path(os.environ.get('LOG_PATH', 'logs'))
    logger.create_logger_file(python_path, log_prefix)

    # get the AWS profile from the environment and use it for all AWS commands
    if 'AWS_DEFAULT_PROFILE' in os.environ or 'AWS_PROFILE' in os.environ:
        if 'AWS_DEFAULT_PROFILE' in os.environ:
            info(
                f'AWS_DEFAULT_PROFILE is set to {os.environ["AWS_DEFAULT_PROFILE"]} and will be used for all AWS commands')
            profile = os.environ['AWS_DEFAULT_PROFILE']
            boto3.setup_default_session(profile_name=profile)
        if 'AWS_PROFILE' in os.environ:
            info(f'AWS_PROFILE is set to {os.environ["AWS_PROFILE"]} and will be used for all AWS commands')
            profile = os.environ['AWS_PROFILE']
            boto3.setup_default_session(profile_name=profile)

    # initialize the config file either from the default or a custom location
    if config:
        custom_config = cfg.Config(config)
    else:
        custom_config = cfg.Config()

    return custom_config


user_name = default_config.get_username()

# example s3 buckets for help
example_input_process_s3 = f's3://{user_name}-video-in-dev'
example_output_process_s3 = f's3://{user_name}-tracks-out-dev'
example_input_train_s3 = f's3://{user_name}-training-dev'
example_output_train_s3 = f's3://{user_name}-model-checkpoints-dev'


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(
    __version__,
    '-V', '--version',
    message=f'%(prog)s, version %(version)s'
)
def cli():
    """
    Process deep sea video in AWS from a command line.
    """
    pass


@cli.command(name="setup")
@click.option('--config', type=str, required=False,
              help=f'Path to config file to override defaults in {default_config_ini}')
@click.option('--mirror', is_flag=True, default=False, help='Mirror docker images from dockerhub into your Elastic '
                                                            'Container Registry (ECR)')
def setup_command(config, mirror):
    """
     Setup your AWS environment. Only need to run this once unless running in a new AWS account.
    """
    init(log_prefix="deepsea_ai_setup")
    custom_config = cfg.Config(config)
    init_db(custom_config)
    account = custom_config.get_account()
    region = custom_config.get_region()
    image_cfg = ['yolov5_container', 'strongsort_container']
    image_tags = [custom_config('docker', t) for t in image_cfg]
    if mirror:
        setup.mirror_docker_hub_images_to_ecr(ecr_client=boto3.client("ecr"), account_id=account,
                                              region=region, image_tags=image_tags)
    setup.create_role(account_id=account)
    setup.store_role(custom_config)

    setup.setup_default_data(custom_config)


@cli.command(name="ecsprocess")
@click.option('-u', '--upload', is_flag=True, default=False,
              help='Set option to upload local video files to S3 bucket')
@click.option('--clean', is_flag=True, default=False,
              help='Clean up unused artifact (e.g. video) from s3 after processing')
@click.option('-i', '--input', type=str, default="/Volumes/M3/mezzanine/DocRicketts/2022/02/1423/",
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg understands. This can also be a single video file.')
@click.option('-e', '--exclude', type=str, multiple=True,
              help='Exclude directory or file. Excludes any directory or file that contains the given string')
@common_args.job_option
@common_args.cluster_option
@common_args.dry_run_option
@cfg_option
@common_args.args
def ecs_process(config, upload, clean, cluster, job, input, exclude, dry_run, args):
    """
     (optional) upload, then batch process in an ECS cluster
    """
    custom_config = init(log_prefix="dsai_ecsprocess", config=config)
    session_maker = init_db(custom_config)
    input_path = Path(input)
    processor = cluster
    video_bucket = 'Unknown'
    resources = None
    if not dry_run:
        resources = custom_config.get_resources(cluster)
        video_bucket = resources['VIDEO_BUCKET']
        processor = resources['PROCESSOR']

    user_name = custom_config.get_username()
    videos = custom_config.check_videos(input_path, exclude)
    tags = custom_config.get_tags(f'Video uploaded from {input} by user {user_name} ')

    total_submitted = 0
    for v in videos:
        loaded = False
        if upload and not loaded:
            if dry_run:
                info(f'Dry run: Uploading {v.name} to S3 bucket {video_bucket}')
            else:
                upload_tag.video_data([v], urlparse(f's3://{video_bucket}'), tags)

        if not loaded:
            if dry_run:
                info(f'Dry run: Submitting {v.name} to cluster for processing with job {job}, cluster {cluster},processor {processor}, user {user_name}, clean {clean}, args {args}')
            else:
                process.batch_run(session_maker, resources, v, job, user_name, clean, args)
            total_submitted += 1
        else:
            warn(f'Video {v.name} has already been processed and loaded...skipping')

    info(f'==== Submitted {total_submitted} videos to {processor} for processing =====')


@cli.command(name="process")
# this might be cleaner as an enum but click does not support that fully yet
@click.option('-i', '--input', type=str, required=True,
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg understands. This can also be a single video file.')
@click.option('-e', '--exclude', type=str, multiple=True,
              help='Exclude directory or file. Excludes any directory or file that contains the given string')
@click.option('--input-s3', type=str, required=True,
              help=f'Path to the s3 bucket with video files. These can be either mp4 or '
                   f'mov files that ffmpeg understands, e.g. s3://{example_input_process_s3}')
@click.option('--output-s3', type=str, required=True,
              help=f'Path to the s3 bucket to store the output, e.g. s3://{example_output_process_s3}')
@click.option('-m', '--model-s3', type=str, default=default_config('aws', 'model'),
              help='S3 location of the trained model tar gz file - must contain a model.tar.gz file with a valid YOLOv5 '
                   'Pytorch model.')
@click.option('--instance-type', type=str, default='ml.g4dn.xlarge',
              help='AWS instance type, e.g. ml.g4dn.xlarge, ml.c5.xlarge')
@common_args.dry_run_option
@common_args.args
@common_args.job_option
@common_args.config_s3_option
@cfg_option
def process_command(config, dry_run, input, exclude, input_s3, output_s3, model_s3, config_s3, job, instance_type, args):
    """
     upload video(s) then process with a model
    """
    custom_config = init(log_prefix="dsai_process", config=config)
    session_maker = init_db(custom_config)

    # get tags to apply to the resources for cost monitoring
    tags = custom_config.get_tags(job)

    input_path = Path(input)
    input_s3 = urlparse(input_s3.rstrip('/'))
    output_s3 = urlparse(output_s3.rstrip('/'))
    model_s3 = urlparse(model_s3.rstrip('/'))

    # create the buckets
    info(f'Creating buckets')

    if bucket.create(input_s3, tags, dry_run) and bucket.create(output_s3, tags, dry_run):

        videos = custom_config.check_videos(input_path, exclude)
        input_s3, size_gb = upload_tag.video_data(videos, input_s3, tags, dry_run)

        # size in GB of the input data should never be < 1
        if size_gb < 1:
            size_gb = 1

        # insert the datetime prefix to make a unique key for the output
        now = datetime.utcnow()
        prefix = now.strftime("%Y%m%dT%H%M%SZ")
        output_unique_s3 = urlparse(f"s3://{output_s3.netloc}/{output_s3.path.lstrip('/')}/{prefix}/")

        # Check if the --save-vid flag is set in the args
        save_vid = False
        if args and 'save_vid' in args:
            save_vid = True

        # estimate the volume size needed for the job; make it 2x the size of the input if saving the video
        if save_vid:
            volume_size_gb = int(2 * size_gb)
        else:
            volume_size_gb = int(1.25 * size_gb)

        # create the arguments for the process script
        process.script_processor_run(session_maker=session_maker,
                                     input_s3=input_s3,
                                     output_s3=output_unique_s3,
                                     model_s3=model_s3,
                                     config_s3=config_s3,
                                     volume_size_gb=volume_size_gb,
                                     instance_type=instance_type,
                                     tags=tags,
                                     dry_run=dry_run,
                                     custom_config=custom_config,
                                     args=args)


@cli.command(name="upload")
@click.option('--config', type=str, default=default_config_ini,
              help=f'Path to config file to override defaults in {default_config_ini}')
@click.option('-i', '--input', type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True,
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg understands.  This can also be a single video file.')
@click.option('--s3', type=str, help='S3 bucket to upload to, e.g. s3://902005-video-in-dev', required=True)
def upload_command(config, input, s3):
    """
    Upload videos
    """
    custom_config = init(log_prefix="dsai_upload", config=config)
    init_db(custom_config)
    input_s3 = urlparse(s3.rstrip('/'))
    tags = custom_config.get_tags(f'Uploaded {input} to {s3}')
    bucket.create(input_s3, tags)
    videos = custom_config.check_videos(Path(input))
    upload_tag.video_data(videos, input_s3, tags)


@cli.command(name="train")
@click.option('--config', type=str, default=default_config_ini,
              help=f'Path to config file to override defaults in {default_config_ini}')
@click.option('--images', type=str, required=True,
              help='Path to compressed training images. Images should be put into a tar.gz file '
                   'that decompress into images/train images/val and optionally images/test. This compressed file should not include any archive artifacts,'
                   ' e.g. ._ files. For example, compress to avoid archives in Mac OSX with'
                   ' COPYFILE_DISABLE=1 tar -czf images.tar.gz images/.  ')
@click.option('--labels', type=str, required=True,
              help='Path to the compressed training labels in YOLO format. Labels should be put into a tar.gz file '
                   'that decompress into labels/. This compressed file should not include any archive artifacts,'
                   ' e.g. ._ files. For example, compress to avoid archives in Mac OSX with'
                   ' COPYFILE_DISABLE=1 tar -czf labels.tar.gz labels/.  ')
@click.option('--label-map', type=str, required=True,
              help='Path to a simple text file with the yolo names in the sorted order of the training label indexes')
@click.option('--input-s3', type=str, required=True,
              help=f'Path to the s3 bucket to save the training data, e.g. {example_input_train_s3} or {example_input_train_s3}')
@click.option('--output-s3', type=str, required=True,
              help=f'Path to the s3 bucket to store the output, e.g. {example_output_train_s3} or {example_output_train_s3}')
@click.option('--resume', type=bool, default=False, help="Resume training from previous run")
@click.option('--model', type=str, default='yolov5x', help=f"Model choice: {','.join(train.models)} ")
@click.option('--epochs', type=int, default=2, help='Number of epochs. Default 2.')
@click.option('--batch-size', type=int, default=2, help='Batch size. Default 2.')
@click.option('--instance-type', type=str, default='ml.p3.2xlarge',
              help='AWS instance type, e.g. ml.p3.2xlarge, ml.p3.8xlarge, ml.p3.16xlarge, ml.p4d.24xlarge')
def train_command(config, images, labels, label_map, input_s3, output_s3, resume, model, epochs, batch_size,
                  instance_type):
    """
     (optional) upload training data, then train a YOLOv5 model
    """
    custom_config = init(log_prefix="dsai_train", config=config)
    init_db(custom_config)

    if instance_type == 'ml.p2.xlarge':
        critical(f'{instance_type} too small for model {model}. Choose ml.p3.2xlarge or better')
        raise Exception(f'{instance_type} too small for model {model}. Choose ml.p3.2xlarge or better')

    # get tags to apply to the resources for cost monitoring
    tags = custom_config.get_tags(f'Training {input_s3} with {model} batch {batch_size} instance {instance_type}')

    image_path = Path(images)
    label_path = Path(labels)
    name_path = Path(label_map)

    # strip off any training forward slashes
    input_s3 = urlparse(input_s3.rstrip('/'))
    output_s3 = urlparse(output_s3.rstrip('/'))

    data = [image_path, label_path, name_path]

    # create the buckets
    if bucket.create(input_s3, tags) and bucket.create(output_s3, tags):

        # upload and return the final bucket prefix to the training data and its total size
        input_training, size_gb = upload_tag.training_data(data, input_s3, tags, cfg.default_training_prefix)

        debug(f"Training data: {input_training} size: {size_gb} GB")

        # insert the datetime prefix to make a unique key for the outputs
        now = datetime.utcnow()
        prefix = now.strftime("%Y%m%dT%H%M%SZ")

        if resume:  # resuming from previous bucket, so no need to set prefix
            ckpts_s3 = urlparse(f"s3://{output_s3.netloc}/{output_s3.path.lstrip('/')}")
            volume_size_gb = int(4 * size_gb + 50)
        else:
            ckpts_s3 = urlparse(f"s3://{output_s3.netloc}/{output_s3.path.lstrip('/')}/{prefix}/checkpoints/")
            volume_size_gb = int(2 * size_gb + 50)
        model_s3 = urlparse(f"s3://{output_s3.netloc}/{output_s3.path.lstrip('/')}/{prefix}/models/")

        # train
        train.yolov5(data, input_training, ckpts_s3, model_s3, epochs, batch_size, volume_size_gb, model, instance_type,
                     custom_config)


@cli.command(name="package")
@click.option('--s3', type=str, required=True,
              help=f"Bucket with the model checkpoints, e.g. s3://{example_output_train_s3}/20220821T005204Z"
              )
def package_command(s3):
    """
    Package a YOLOv5 model into a format that the deepsea-ai can use in its pipelines.
    This is done at the end of the train command automatically and stored in a model.tar.gz file.
    This is added in case checkpoints were generated outside the training command, e.g. SageMaker Studio. Colab
    """
    init(log_prefix="dsai_package")
    train.package(urlparse(s3.rstrip('/')))


@cli.command(name="split")
@click.option('-i', '--input', type=str, required=True,
              help='Path to the root folder with images and labels, organized into labels/ and images/ folders files to split')
@click.option('-o', '--output', type=str, required=True,
              help='Path to the root folder to save the split, compressed files. If it does not exist, it will be created.')
def split_command(input: str, output: str):
    """
    Split data into train/val/test sets randomly per the following percentages 85%/10%/5%
    """
    init(log_prefix="dsai_split")
    input_path = Path(input)
    output_path = Path(output)

    if not output_path.exists():
        output_path.mkdir(parents=True)

    paths = [input_path / 'labels', input_path / 'images']

    exists = [not p.exists() for p in paths]
    if any(exists):
        err(f'Error: one or more {paths} missing')
        return

    train.split(Path(input), Path(output))


@cli.command(name="monitor")
@click.option('--cluster', type=str, required=True,
              help='Name of the cluster to query.  This must correspond to an available Elastic '
                   'Container Service cluster.')
@click.option('--config', type=str, required=False,
              help=f'Path to config file to override defaults in {default_config_ini}')
@click.option('--report-path', type=str, required=False, default=default_report_dir,
              help=f'Path to save reports to. Defaults to {default_report_dir}')
@click.option('--timeout-period', type=int, help='Timeout for monitoring in seconds; default is never')
@click.option('--update-period', type=int, default=10, help='Update period to monitor a job; default is every 60 '
                                                            'seconds. Ignored if --job is not specified.Generates a '
                                                            'new report file in the reports/ folder')
def monitor_command(cluster: str, config, update_period: int, timeout_period: int, report_path: str):
    """
    Print monitoring information for the cluster
    """
    custom_config = init(log_prefix="dsai_monitor", config=config)
    session_maker = init_db(custom_config)
    resources = custom_config.get_resources(cluster)
    if not resources:
        err(f'No resources found for cluster {cluster}')
        return
    report_path = Path(report_path)

    while True:
        with session_maker.begin() as db:
            # Get all the jobs
            num_jobs = len(db.query(Job).filter(Job.job_type == JobType.ECS).all())
            info(f'Found {num_jobs} jobs in the database with type {JobType.ECS}.')

        if num_jobs > 0:
            info(f'Monitoring {num_jobs} job')
            m = monitor.Monitor(session_maker, report_path, resources, update_period)
            m.start()
            m.join(timeout_period)
        else:
            info(f'No jobs found in the database with type {JobType.ECS}. Checking again in 30 seconds. Ctrl-C to stop.')
            time.sleep(30)


if __name__ == '__main__':
    try:
        start = datetime.utcnow()
        cli()
        end = datetime.utcnow()
        info(f'Done. Elapsed time: {end - start} seconds')
    except Exception as e:
        err(f'Exiting. Error: {e}')
        exit(-1)
