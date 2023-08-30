# deepsea-ai, Apache-2.0 license
# Filename: database/job/database_helper.py
# Description: Job database
from datetime import datetime

from sqlalchemy.orm import Session

from deepsea_ai.database.job.database import Job, PydanticJobWithMedias, PydanticMedia, Media
from deepsea_ai.database.job.misc import Status
from deepsea_ai.logger import info


def get_status(job: Job) -> bool:
    """
    Get the status of a job
    :param job: The job to get the status of
    :return: The status of the job
    """

    pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)

    # Get the status of all the medias
    statuses = [m.status for m in pydantic_job_with_medias.medias]

    # if any of the statuses are RUNNING, the job should be RUNNING
    if Status.RUNNING in statuses:
        return Status.RUNNING

    # if all the statuses are QUEUED, the job should be QUEUED
    if all([s == Status.QUEUED for s in statuses]):
        return Status.QUEUED

    # if any of the statuses are FAILED, the job should be FAILED
    if Status.FAILED in statuses:
        return Status.FAILED


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


def update_media(db: Session, job: Job, video_name: str, status: str) -> Media:
    """
    Update a video in a job. If the video does not exist, add it to the job.
    :param db: The database session
    :param job: The job
    :param video_name: The name of the video to update
    :param status: The status of the video
    """

    info(f'Updating media {video_name} to {status}')
    job_p = PydanticJobWithMedias.from_orm(job)

    # Get the media with the name and update the timestamp and status
    media_p = [m for m in job_p.medias if m.name == video_name]
    if media_p:
        info(f'Found media {video_name} in job {job.name}')
        # Get the media object by its id
        media = db.query(Media).filter(Media.id == media_p[0].id).first()
        # Update the media status and timestamp
        media.status = status
        media.updatedAt = datetime.utcnow()
        db.merge(media)
        db.commit()
        return media
    else:
        info(f'A new media {video_name} was added to job {job.name}')
        new_media = Media(name=video_name, status=Status.SUCCESS, job=job)
        db.add(new_media)
        job.medias.append(new_media)
        db.commit()
        return new_media
