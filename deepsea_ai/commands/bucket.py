# !/usr/bin/env python
__author__ = "Danelle Cline"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Bucket utilities

@author: __author__
@status: __status__
@license: __license__
'''
import logging
import boto3
from botocore.exceptions import ClientError


def create(bucket:tuple, tags: dict):
    """Create an S3 bucket
    :param bucket: Bucket to create
    :param tags: Tags to assign to the bucket
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        session = boto3.session.Session()
        s3_client = boto3.client('s3', region_name=session.region_name)
        location = {'LocationConstraint': session.region_name}
        s3_client.create_bucket(Bucket=bucket.netloc,
                                CreateBucketConfiguration=location)

        try:
            s3_client.put_bucket_tagging(Bucket=bucket.netloc, Tagging={'TagSet': tags})
        except Exception as error:
            raise error
    except ClientError as e:
        if e.response['Error']['Code'] != "BucketAlreadyOwnedByYou":
            logging.error(e)
        return False
    return True


def download(bucket_name:str, prefix: str):
    """Download an object by its prefix from a bucket
    :param bucket_name: Bucket to create
    :param prefix: Prefix to download
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        session = boto3.session.Session()
        s3_client = boto3.client('s3', region_name=session.region_name)
        location = {'LocationConstraint': session.region_name}
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration=location)

        try:
            s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': tags})
        except Exception as error:
            raise error
    except ClientError as e:
        if e.response['Error']['Code'] != "BucketAlreadyOwnedByYou":
            logging.error(e)
        return False
    return True

def size(bucket:tuple) -> int:
    """
    Get the total size in GB of the bucket.
    :param bucket: Bucket name to searc
    :return: Total size in bytes
    """
    size_gb = 0
    session = boto3.session.Session()
    s3 = session.resource('s3')
    b = s3.Bucket(bucket.netloc)

    for object in b.objects.filter(Prefix=bucket.path.split('/')[-1]):
        folder = object.key.split('/')[0]
        size_gb += object.size

    return size_gb