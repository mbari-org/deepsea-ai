# !/usr/bin/env python
__author__ = "Danelle Cline"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Main entry point for deepsea-ai

@author: __author__
@status: __status__
@license: __license__
'''

import click
from datetime import datetime
from pathlib import Path
import sys
import numpy as np
from urllib.parse import urlparse

from deepsea_ai.commands import upload_tag, config, process, train, bucket
from deepsea_ai.database import api, queries
from deepsea_ai import __version__

# example s3 buckets for help
example_input_process_s3 = 's3://902005-video-in-dev'
example_output_process_s3 = 's3://902005-tracks-out-dev'
example_input_train_s3 = 's3://902005-training-dev'
example_output_train_s3 = 's3://902005-model-checkpoints-dev'


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


@cli.command(name="ecsprocess")
@click.option('--endpoint', required=False, help='Set to the database endpoint to check if any video has already '
                                                 'been processed and loaded before sending off a job')
@click.option('-u', '--upload', is_flag=True, default=False,
              help='Set option to upload local video files to S3 bucket')
@click.option('--clean', is_flag=True, default=True,
              help='Clean up unused artifact (e.g. video) from s3 after processing')
@click.option('-i', '--input', type=str, default="/Volumes/M3/mezzanine/DocRicketts/2022/02/1423/",
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg '
                   'understands.')
@click.option('--cluster', type=str, default='lonny33k',
              help='Name of the cluster to use to batch process.  This must correspond to an available Elastic '
                   'Container Service cluster.')
@click.option('--job', type=str, default='lonny33k',
              help='Name of the job, e.g. DiveV4361 benthic outline')
def batchprocess_command(endpoint, upload, clean, cluster, job, input):
    """
     (optional) upload, then batch process in an ECS cluster
    """
    database = None
    if endpoint:
        database = api.DeepSeaAIClient(endpoint)

    input_path = Path(input)
    resources = config.get_resources(cluster)
    user_name = config.get_username()

    for v in videos:
        loaded = False
        if database:
            # Check if the video has already been loaded by looking it up by the media name per this job name
            medias = database.execute(queries.GET_MEDIA_IN_JOB,
                                      processing_job_name=f"{resources['processor']}-“{job_name}”",
                                      media_name=v.name)

            # Found a media in the job as keyed by the processing name, so assume that this was already processed
            if len(medias['data']['mediaInJob']) > 0:
                loaded = True

        if upload and not loaded:
            upload_tag.run([v], resources['VIDEO_BUCKET'], user_name)

        if not loaded:
            process.batch_run(resources, v, job, user_name, clean)
        else:
            print(f'Video {v.name} has already been processed and loaded...skipping')


@cli.command(name="process")
@click.option('-u', '--upload', is_flag=True, default=True,
              help='Set option to upload local video files to S3 bucket')
 # this might be cleaner as an enum but click does not support that fully yet
@click.option('--tracker', default='deepsort',
              help='Tracking type: deepsort or strongsort')
@click.option('-i', '--input', type=str, required=True,
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg understands.')
@click.option('--input-s3', type=str, required=True,
              help=f'Path to the s3 bucket with video files. These can be either mp4 or '
                                               f'mov files that ffmpeg understands, e.g. s3://{example_input_process_s3}')
@click.option('--output-s3', type=str, required=True,
              help=f'Path to the s3 bucket to store the output, e.g. s3://{example_output_process_s3}')
@click.option('-m', '--model-s3', type=str, default=process.default_model_s3,
              help='S3 location of the trained model tar gz file - must contain a model.tar.gz file with a valid YOLOv5 '
                   'Pytorch model.')
@click.option('-c', '--config-s3', type=str, help='S3 location of tracking algorithm config yaml file')
@click.option('--model-size', type=click.INT, default=640, help='Size of the model, e.g. 640 or 1280')
@click.option('--conf-thres', type=click.FLOAT, default=.01, help='Confidence threshold for the model')
@click.option('-s', '--save-vid', is_flag=True, default=False,
              help='Set option to output original video with detection boxes overlaid.')
@click.option('--instance-type', type=str, default='ml.p3.xlarge', help='AWS instance type, e.g. ml.p2.xlarge, ml.p3.2xlarge, ml.p3.8xlarge, ml.p3.16xlarge, ml.p4d.24xlarge')
def process_command(upload, tracker, input, input_s3, output_s3, model_s3, config_s3, model_size, conf_thres,
                    save_vid, instance_type):
    """
     (optional) upload, then process video with a model
    """
    if instance_type == 'ml.p2.xlarge':
        raise Exception(f'{instance_type} too small. Choose ml.p3.2xlarge or better')

    input_path = Path(input)
    input_s3 = urlparse(input_s3)
    output_s3 = urlparse(output_s3)
    model_s3 = urlparse(model_s3)

    # get tags to apply to the resources for cost monitoring
    tags = config.get_tags()

    # create the buckets
    print(f'Creating buckets')
    bucket.create(input_s3, tags)
    bucket.create(output_s3, tags)

    if upload:
        videos = config.check_videos(input_path)
        upload_tag.video_data(videos, input_s3, tags)
 
    # insert the datetime prefix to make a unique key for the output
    now = datetime.utcnow()
    prefix = now.strftime("%Y%m%dT%H%M%SZ")
    output_unique_s3 = urlparse(f"s3://{output_s3.netloc}{output_s3.path}/{prefix}/")

    volume_size_gb = 10
    
    process.script_processor_run(input_s3, output_unique_s3, model_s3, model_size, volume_size_gb, instance_type,
                                 config_s3, save_vid, conf_thres, tracker)


@cli.command(name="upload")
@click.option('-i', '--input', type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True,
              help='Path to the folder with video files to upload. These can be either mp4 or mov files that '
                   'ffmpeg understands.')
@click.option('--s3', type=str, help='S3 bucket to upload to, e.g. s3://902005-video-in-dev', required=True)
def upload_command(input, s3):
    """
    Upload videos
    """
    input_path = Path(input)
    input_s3 = urlparse(s3)
    tags = config.get_tags()
    bucket.create(input_s3, tags)
    videos = config.check_videos(Path(input))

    upload_tag.video_data(videos, input_s3, tags)


@cli.command(name="train")
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
              help=f'Path to the s3 bucket to save the training data, e.g. s3://{example_input_train_s3} or {example_input_train_s3}')
@click.option('--output-s3', type=str, required=True,
              help=f'Path to the s3 bucket to store the output, e.g. s3://{example_output_train_s3} or {example_output_train_s3}')
@click.option('--resume', type=bool, default=False, help="Resume training from previous run")
@click.option('--model', type=str, default='yolov5x', help=f"Model choice: {','.join(train.models)} " )
@click.option('--epochs', type=int, default=2, help='Number of epochs. Default 2.')
@click.option('--batch-size', type=int, default=2, help='Batch size. Default 2.')
@click.option('--instance-type', type=str, default='ml.p3.2xlarge', help='AWS instance type, e.g. ml.p3.2xlarge, ml.p3.2xlarge, ml.p3.8xlarge, ml.p3.16xlarge, ml.p4d.24xlarge')
def train_command(images, labels, label_map, input_s3, output_s3, resume, model, epochs, batch_size, instance_type):
    """
     (optional) upload training data, then train a YOLOv5 model
    """
    if instance_type == 'ml.p2.xlarge':
        raise Exception(f'{instance_type} too small for model {model}. Choose ml.p3.2xlarge or better')

    image_path = Path(images)
    label_path = Path(labels)
    name_path = Path(label_map)

    # strip off any s3 prefixes
    input_s3 = urlparse(input_s3)
    output_s3 = urlparse(output_s3)

    data = [image_path, label_path, name_path]

    # get tags to apply to the resources for cost monitoring
    tags = config.get_tags()

    # create the buckets
    bucket.create(input_s3, tags)
    bucket.create(output_s3, tags)

    # upload and return the final bucket prefix to the training data and its total size
    input_training, size_gb = upload_tag.training_data(data, input_s3, tags)

    # guess on how much volume is needed per each GB
    volume_size_gb = int(size_gb/20)

    # insert the datetime prefix to make a unique key for the outputs
    now = datetime.utcnow()
    prefix = now.strftime("%Y%m%dT%H%M%SZ")

    if resume: # resuming from previous bucket, so no need to set prefix
        ckpts_s3 = urlparse(f"s3://{output_s3.netloc}{output_s3.path.lstrip('/')}")
    else:
        ckpts_s3 = urlparse(f"s3://{output_s3.netloc}{output_s3.path.rstrip('/')}/{prefix}/checkpoints/")
    model_s3 = urlparse(f"s3://{output_s3.netloc}{output_s3.path.rstrip('/')}/{prefix}/models/")

    # train
    train.yolov5(data, input_training, ckpts_s3, model_s3, epochs, batch_size, volume_size_gb,  model, instance_type)


@cli.command(name="package")
@click.option('--s3', type=str,  required=True,
              help=f"Bucket with the model checkpoints, e.g. s3://{example_output_train_s3}/20220821T005204Z"
              )
def package_command(s3):
    train.package(urlparse(s3))

@cli.command(name="split")
@click.option('-i', '--input', type=str, required=True,
              help='Path to the root folder with images and labels, organized into labels/ and images/ folders files to split')
@click.option('-o', '--output', type=str, required=True,
              help='Path to the root folder to save the split, compressed files. If it does not exist, it will be created.')
def split_command(input:str, output:str):
    """
    split data into train/val/test sets randomly per the following percentages 85%/10%/5%
    """
    input_path = Path(input)
    output_path = Path(output)

    if not output_path.exists():
        output_path.mkdir(parents=True)

    paths = [input_path / 'labels', input_path / 'images']

    exists = [not p.exists() for p in paths]
    if any(exists):
        print (f'Error: one or more {paths} missing')
        return

    train.split(Path(input), Path(output))

if __name__ == '__main__':
    cli()
