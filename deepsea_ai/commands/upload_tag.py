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

import botocore
import boto3
import deepsea_ai.config as config
from pathlib import Path
from urllib.parse import urlparse

from . import bucket


def video_data(videos: [], input_s3:tuple, tags:dict):
    """
     Does an upload and tagging of a collection of videos to S3
    :param videos: Array of video files in the input_path to upload
    :param input_s3: Base bucket to upload to, e.g. 902005-video-in-dev
    :param tags: Tags to assign to the video
    :return: Uploaded bucket path, Size in GB of video data
    """

    s3 = boto3.client('s3')
    s3_resource = boto3.resource('s3')

    # upload and tag the video objects individually
    for v in videos:
        prefix_path = v.parent.as_posix().split("Volumes/")[-1].lstrip('/') ## get Directory string
        target_prefix = f'{input_s3.path}{prefix_path}/{v.name}'

        # check if the video exists in s3
        try:
            s3_resource.Object(input_s3.netloc, target_prefix).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The video does not exist so upload
                try:
                    with open(v.as_posix(), "rb") as f:
                        print(f'Uploading {v} to s3://{input_s3.netloc}/{target_prefix}...')
                        s3.upload_fileobj(f, input_s3.netloc, target_prefix)
                except: print("error in uploading to s3")
            else:
                raise
        else:
            # the video does exist.
            print(f'Found s3://{input_s3.netloc}/{target_prefix} ...skipping upload')

        try:
            # tag it
            s3.put_object_tagging(Bucket=input_s3.netloc, Key=f'{target_prefix}', Tagging={'TagSet': tags})
        except Exception as error:
            raise error

        output = urlparse(f's3://{input_s3.netloc}/{prefix_path}/', allow_fragments=True)
        size_gb = bucket.size(output)
        return output, size_gb

def training_data(data: [Path], input:tuple, tags:dict, training_prefix:str):
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

    prefix_path = None

    for d in data:
        if not d.exists():
            print(f"Error: {d} does not exist")
            exit(-1)
            
    for d in data:
        # arbitrarily pick the first element to form a prefix; it does not matter but can serve as an intuitive
        # way to reference later.
        if not prefix_path:
            prefix_path = d.parent.as_posix().split("Volumes/")[-1].lstrip('/')

        # check if the data exists in s3
        # all the data needs to be under the same prefix for training
        target_prefix = f'{prefix_path}/{training_prefix}/{d.name}'
        try:
            s3_resource.Object(input.netloc, target_prefix).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The data does not exist so upload
                try:
                    with open(d.as_posix(), "rb") as f:
                        print(f'Uploading {d} to s3://{input.netloc}/{target_prefix}...')
                        s3.upload_fileobj(f, input.netloc, target_prefix)
                except Exception as error:
                    print(f"Error {error} uploading to s3")
            else:
                raise
        else:
            # the data already exist so skip over it
            print(f'Found s3://{input.path}/{target_prefix} ...skipping upload')

        try:
            # tag it
            s3.put_object_tagging(Bucket=input.netloc, Key=target_prefix, Tagging={'TagSet': tags})
        except Exception as error:
            raise error

    output = urlparse(f's3://{input.netloc}/{prefix_path}/{training_prefix}/')
    size_gb = bucket.size(output)

    return output, size_gb
