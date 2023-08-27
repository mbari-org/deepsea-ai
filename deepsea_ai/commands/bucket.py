# deepsea-ai, Apache-2.0 license
# Filename: commands/bucket.py
# Description: S3 bucket utilities

import logging
import boto3
import numpy as np
from botocore.exceptions import ClientError
from deepsea_ai.logger import info


def create(bucket: tuple, tags: dict, dry_run: bool = False):
    """Create an S3 bucket
    :param bucket: Bucket to create
    :param tags: Tags to assign to the bucket
    :return: True if bucket created, or it already exists, else False
    """
    if dry_run:
        info(f'dry-run: Would have created bucket {bucket.netloc} with tags {tags}')
        return True

    # Create bucket
    try:
        info(f'Creating bucket {bucket.netloc}...')
        session = boto3.session.Session()
        s3_client = boto3.client('s3', region_name=session.region_name)
        location = {'LocationConstraint': session.region_name}
        s3_client.create_bucket(Bucket=bucket.netloc,
                                CreateBucketConfiguration=location)

        try:
            s3_client.put_bucket_tagging(Bucket=bucket.netloc, Tagging={'TagSet': tags})
        except Exception as error:
            raise f'Error creating bucket {bucket.netloc} {error}'
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == "BucketAlreadyOwnedByYou" or code == 'BucketAlreadyExists':
            logging.info(e)
            return True

        logging.error(e)
        return False
    return True


def size(bucket: tuple) -> int:
    """
    Get the total size in GB of the bucket.
    :param bucket: Bucket name to searc
    :return: Total size in gigabytes
    """
    size_gb = 0
    session = boto3.session.Session()
    s3 = session.resource('s3')
    b = s3.Bucket(bucket.netloc)

    for object in b.objects.filter(Prefix=bucket.path.split('/')[-1]):
        object.key.split('/')[0]
        size_gb += object.size

    return max(np.round(size_gb / 1e9), 1)
