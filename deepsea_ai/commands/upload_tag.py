# !/usr/bin/env python
__author__ = "Danelle Cline, Duane Edgington"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Bucket upload and tagging utility

@author: __author__
@status: __status__
@license: __license__
'''

from datetime import datetime

import botocore
import boto3
import time
from pathlib import Path
from urllib.parse import urlparse
from deepsea_ai.logger import info, err, debug, critical, exception, keys

from . import bucket


def video_data(videos: list[Path], input_s3: tuple, tags: dict, dry_run: bool = False):
    """
     Does an upload and tagging of a collection of videos to S3
    :param videos: Array of video files in the input_path to upload
    :param input_s3: Base bucket to upload to, e.g. 902005-video-in-dev
    :param tags: Tags to assign to the video
    :param dry_run: If true, do not upload or tag
    :return: Uploaded bucket path, Size in GB of video data
    """
    if dry_run:
        for v in videos:
            info(f'dry-run: Would have uploaded {v.as_posix()} to {input_s3.netloc} with tags {tags}')
        return urlparse(f's3://{input_s3.netloc}/{get_prefix(videos[0])}/', allow_fragments=True), 0

    s3 = boto3.client('s3')
    s3_resource = boto3.resource('s3')

    # upload and tag the video objects individually
    for v in videos:
        prefix_path = get_prefix(v)
        if input_s3.path:
            target_prefix = f"{input_s3.path}/{prefix_path.lstrip('/')}/{v.name}"
        else:
            target_prefix = f"{prefix_path.lstrip('/')}/{v.name}"

        # check if the video exists in s3
        try:
            s3_resource.Object(input_s3.netloc, target_prefix).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                upload_success = False
                # The video does not exist so upload and retry
                for retry in range(10):
                    try:
                        with open(v.as_posix(), "rb") as f:
                            info(f'Uploading {v} to s3://{input_s3.netloc}/{target_prefix}...')
                            s3.upload_fileobj(f, input_s3.netloc, target_prefix)
                            upload_success = True
                            break
                    except e:
                        exception(e)
                        exception(f"Error uploading {v} to s3. Retrying every 60 seconds...")
                        time.sleep(60)

                if not upload_success:
                    critical(f"Error uploading {v} to s3 after {retry} retries. Aborting.")
                    raise Exception(f"Error uploading {v} to s3 after {retry} retries. Aborting.")
            else:
                exception(e)
                raise
        else:
            # the video does exist.
            info(f'Found s3://{input_s3.netloc}/{target_prefix} ...skipping upload')

        try:
            # tag it
            info(f'Tagging {v} with {tags}...')
            s3.put_object_tagging(Bucket=input_s3.netloc, Key=f'{target_prefix}', Tagging={'TagSet': tags})
        except Exception as error:
            raise error

        output = urlparse(f's3://{input_s3.netloc}/{prefix_path}/', allow_fragments=True)
        size_gb = bucket.size(output)
        return output, size_gb


def training_data(data: [Path], input: tuple, tags: dict, training_prefix: str):
    """
     Does an upload and tagging of training data to S3
    :param data: Paths to training data to upload
    :param input: Bucket to upload to
    :param bucket: Tags to assign to the video
    :param training_prefix: Training prefix to append to the bucket upload
    :return: Uploaded bucket path, Size in GB of training data
    """

    # upload and tag the video objects individually
    s3 = boto3.client('s3')
    s3_resource = boto3.resource('s3')

    for d in data:
        if not d.exists():
            err(f"Error: {d} does not exist")
            exit(-1)

    for d in data:
        # check if the data exists in s3
        # all the data needs to be under the same prefix for training
        target_prefix = f'{training_prefix}/{d.name}'
        try:
            s3_resource.Object(input.netloc, target_prefix).load()
        except botocore.exceptions.ClientError as e:
            info(f'{e} {d} does not exist in s3://{input.netloc}/{target_prefix}. Uploading...')
            if e.response['Error']['Code'] == "404":
                # The data does not exist so upload
                try:
                    with open(d.as_posix(), "rb") as f:
                        info(f'Uploading {d} to s3://{input.netloc}/{target_prefix}...')
                        s3.upload_fileobj(f, input.netloc, target_prefix)
                except Exception as error:
                    error(f"Error {error} uploading to s3")
            else:
                raise
        else:
            # the data already exist so skip over it
            info(f'Found s3://{input.path}/{target_prefix} ...skipping upload')

        try:
            # tag it
            s3.put_object_tagging(Bucket=input.netloc, Key=target_prefix, Tagging={'TagSet': tags})
        except Exception as error:
            exception(error)
            raise error

    output = urlparse(f"s3://{input.netloc}/{training_prefix}/")
    size_gb = bucket.size(output)

    return output, size_gb


def get_prefix(path: Path):
    """
    Get the prefix from a path, stripping away any volume or drive information
    :param path: Path to get the prefix from
    :return: Prefix
    """
    prefix = None
    for m in ['Volumes/', 'mnt/', 'Users/', 'home/']:
        if m in path.as_posix():
            prefix = path.parent.as_posix().split(m)[-1].lstrip('/')
            break

    # Do not allow empty prefixes
    if not prefix:
        prefix = '/'
    return prefix
