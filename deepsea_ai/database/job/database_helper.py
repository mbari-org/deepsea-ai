# deepsea-ai, Apache-2.0 license
# Filename: database/job/database_helper.py
# Description: Job database

import json
import base64
from datetime import datetime
from sqlalchemy.orm import Session

from deepsea_ai.database.job.database import Job, PydanticJobWithMedias, Media
from deepsea_ai.database.job.misc import Status
from deepsea_ai.logger import info


def json_b64_encode(obj):
    """
    Convert a JSON object to a base64 encoded string
    :param obj: The JSON object to convert
    :return: The base64 encoded string
    """
    json_str = json.dumps(obj)
    encoded = base64.b64encode(json_str.encode()).decode()
    return encoded


def json_b64_decode(obj):
    """
    Decode a base64 encoded JSON string
    :param obj: The base64 encoded JSON string
    :return: The decoded JSON object
    """
    decoded = base64.b64decode(obj).decode()
    return json.loads(decoded)


def get_status(job: Job) -> bool:
    """
    Get the status of a job
    :param job: The job to get the status of
    :return: The status of the job
    """

    # Get the status of all the medias
    statuses = [m.status for m in job.media]

    # if any of the medias are RUNNING, the job should be RUNNING
    if Status.RUNNING in statuses:
        return Status.RUNNING

    # if any the medias are QUEUED, the job should be QUEUED
    if Status.QUEUED in statuses:
        return Status.QUEUED

    # if any of the statuses are FAILED, the job should be FAILED
    if Status.FAILED in statuses:
        return Status.FAILED

    # if all are SUCCESS, the job should be SUCCESS
    num_success = statuses.count(Status.SUCCESS)
    if num_success == len(statuses):
        return Status.SUCCESS

    return Status.UNKNOWN


def get_num_failed(job: Job) -> int:
    """
    Get the number of failed medias in a job
    :param job: The job to get the number of failed medias from
    :return: The number of failed medias in the job
    """

    # Get the status of all the medias
    statuses = [m.status for m in job.media]

    # Count the number of FAILED medias
    num_failed = statuses.count(Status.FAILED)

    return num_failed


def get_num_completed(job: Job) -> int:
    """
    Get the number of completed medias in a job
    :param job: The job to get the number of failed medias from
    :return: The number of completed medias in the job
    """

    # Get the status of all the medias
    statuses = [m.status for m in job.media]

    # Count the number of SUCCESS medias
    num_completed = statuses.count(Status.SUCCESS)

    return num_completed


def get_job_by_name(db: Session, job_name: str) -> Job:
    """
    Get a job from the database by its name
    """
    # Get all the jobs with the same name
    return db.query(Job).filter(Job.name == job_name).first()


def get_job_by_uuid(db: Session, job_uuid: str) -> Job:
    """
    Get a job from the database by its uuid
    """
    # Get all the jobs with the same uuid
    return db.query(Job).filter(Job.uuid == job_uuid).first()


def update_media(db: Session, job: Job, video_name: str, status: str, **kwargs):
    """
    Update a video in a job. If the video does not exist, add it to the job.
    :param db: The database session
    :param job: The job
    :param video_name: The name of the video to update
    :param status: The status of the video
    """
    info(f'Updating media {video_name} to {status}')

    # Set kwargs to empty dict if None
    kwargs = kwargs or {}

    # If there are additional kwargs, search by them and the name
    media = None
    if kwargs:
        if 'metadata_b64' in kwargs:
            # Find the media with the matching metadata
            media = [m for m in job.media if m.metadata_b64 == kwargs['metadata_b64'] and m.name == video_name]
        else:
            for key, value in kwargs.items():
                for m in job.media:
                    if m.metadata_b64 and json_b64_decode(m.metadata_b64)[key] == value and m.name == video_name:
                        info(f'Found media matching {video_name} and {key} {value} in job {job.name}')
                        media = m
                        break
    if not media:  # can't find by metadata, try by name
        media = [m for m in job.media if m.name == video_name]

    if media:
        if len(media) > 0:
            media = media[0]

        info(f'Found media {video_name} in job {job.name}')

        if status == Status.QUEUED and media.status == Status.RUNNING or media.status == Status.SUCCESS or media.status == Status.FAILED:
            info(f'Media {video_name} in job {job.name} is already {media.status}. Not updating to {status}')
            return

        # Update the media status, timestamp and any additional kwargs
        media.status = status
        media.updatedAt = datetime.utcnow()

        # add metadata if there was one in the kwargs
        if 'metadata_b64' in kwargs:
            media.metadata_b64 = kwargs['metadata_b64']
        else:
            media.metadata_b64 = json_b64_encode(kwargs)

        # Update the metadata
        metadata_json = json_b64_decode(media.metadata_b64)
        for key, value in kwargs.items():
            if key in metadata_json:
                metadata_json[key] = value
        media.metadata_b64 = json_b64_encode(metadata_json)

        db.merge(media)

    else:
        info(f'A new media {video_name} was added to job {job.name} kwargs {kwargs}')
        new_media = Media(name=video_name,
                          status=status,
                          job=job,
                          metadata_b64=json_b64_encode(kwargs),
                          updatedAt=datetime.utcnow())
        db.add(new_media)
        job.media.append(new_media)
