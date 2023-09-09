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

    pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)

    # Get the status of all the medias
    statuses = [m.status for m in pydantic_job_with_medias.medias]

    # if any of the medias are RUNNING, the job should be RUNNING
    if Status.RUNNING in statuses:
        return Status.RUNNING

    # if any the medias are QUEUED, the job should be QUEUED
    if Status.QUEUED in statuses:
        return Status.QUEUED

    # if any of the statuses are FAILED, the job should be FAILED
    if Status.FAILED in statuses:
        return Status.FAILED

    return Status.UNKNOWN


def get_num_failed(job: Job) -> int:
    """
    Get the number of failed medias in a job
    :param job: The job to get the number of failed medias from
    :return: The number of failed medias in the job
    """

    pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)

    # Get the status of all the medias
    statuses = [m.status for m in pydantic_job_with_medias.medias]

    # Count the number of FAILED medias
    num_failed = statuses.count(Status.FAILED)

    return num_failed


def get_num_completed(job: Job) -> int:
    """
    Get the number of completed medias in a job
    :param job: The job to get the number of failed medias from
    :return: The number of completed medias in the job
    """

    pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)

    # Get the status of all the medias
    statuses = [m.status for m in pydantic_job_with_medias.medias]

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
    # If the job has medias, get the media with the name
    if job.medias:
        job_p = PydanticJobWithMedias.from_orm(job)

        # If there are additional kwargs, search by them
        if kwargs:
            for key, value in kwargs.items():
                media_p = [m for m in job_p.medias if json_b64_decode(m.metadata_b64)[key] == value and m.name == video_name]
                info(f'Found {len(media_p)} media matching {video_name} and {key} {value} in job {job.name}')
                if len(media_p) > 0:
                    break
        else:
            # Get the media with the name
            media_p = [m for m in job_p.medias if m.name == video_name]

        if len(media_p) > 0:
            media_p = [m for m in job_p.medias if m.name == video_name]
            info(f'Found {len(media_p)} media matching {video_name} in job {job.name}')

            # pick the first one
            media_id = media_p[0].id

            info(f'Found media {video_name} in job {job.name}')
            media = db.query(Media).filter(Media.id == media_id).first()

            # Update the media status, timestamp and any additional kwargs
            media.status = status
            media.updatedAt = datetime.utcnow()

            # Update the metadata
            if media.metadata_b64 and kwargs:
                metadata_json = json_b64_decode(media.metadata_b64)
                for key, value in kwargs.items():
                    if key in metadata_json:
                        metadata_json[key] = value
                media.metadata_b64 = json_b64_encode(metadata_json)
            if kwargs and not media.metadata_b64: # add metadata if it doesn't exist
                media.metadata_b64 = json_b64_encode(kwargs)

            db.merge(media)
            db.commit()
        else:
            info(f'A new media {video_name} was added to job {job.name} {kwargs}')
            if kwargs:
                new_media = Media(name=video_name,
                                  status=Status.QUEUED,
                                  job=job,
                                  metadata_b64=json_b64_encode(kwargs),
                                  updatedAt=datetime.utcnow())
            else:
                new_media = Media(name=video_name,
                                  status=Status.QUEUED,
                                  job=job,
                                  updatedAt=datetime.utcnow())
            db.add(new_media)
            job.medias.append(new_media)
            db.commit()
    else:
        if kwargs:
            info(f'A new media {video_name} was added to job {job.name} {kwargs}')
            new_media = Media(name=video_name,
                              status=Status.QUEUED,
                              job=job,
                              metadata_b64=json_b64_encode(kwargs),
                              updatedAt=datetime.utcnow())
        else:
            info(f'A new media {video_name} was added to job {job.name}')
            new_media = Media(name=video_name,
                              status=Status.QUEUED,
                              job=job,
                              updatedAt=datetime.utcnow())
        db.add(new_media)
        job.medias.append(new_media)
        db.commit()