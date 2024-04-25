# Test the sqlite database with pydantic
import time
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import Job, PydanticJobWithMedias, PydanticJob, Media, PydanticMedia, init_db
from deepsea_ai.database.job.database_helper import json_b64_encode, json_b64_decode, get_status, get_num_failed, \
    update_media, get_num_completed
from deepsea_ai.database.job.misc import JobType, Status, job_hash
from deepsea_ai.logger import CustomLogger

global session_maker

# Set up the logger
CustomLogger(output_path=Path.cwd() / 'logs', output_prefix=__name__)

@pytest.fixture
def setup_database():
    cfg = Config()
    global session_maker
    # Reset the database
    session_maker = init_db(cfg, reset=True)
    name = "Dive 1377 with yolov5x-mbay-benthic"

    job = Job(id=1,
              engine="test",
              name=name,
              job_type=JobType.ECS)
    vid1 = Media(name="vid1.mp4", status=Status.QUEUED,
                 metadata_b64=json_b64_encode({"job_uuid": job_hash("vid1.mp4")}))
    vid2 = Media(name="vid2.mp4", status=Status.SUCCESS,
                 metadata_b64=json_b64_encode({"job_uuid": job_hash("vid2.mp4")}))
    job.media = [vid1, vid2]
    with session_maker.begin() as db:
        db.add(job)
    yield
    # Reset the database
    init_db(cfg, reset=True)


def test_pydantic_sqlalchemy(setup_database):
    """
    Test that the sqlalchemy models can be converted to pydantic models and back
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)
        data = pydantic_job_with_medias.dict()
        # Remove the timestamps as they are not in the sqlalchemy model
        del data['createdAt']
        for media in data['media']:
            del media['createdAt']

        assert data == {
            "engine": "test",
            "id": 1,
            "name": "Dive 1377 with yolov5x-mbay-benthic",
            "job_type": JobType.ECS,
            "media": [
                {"name": "vid1.mp4",
                 "id": 1,
                 "job_id": 1,
                 "status": Status.QUEUED,
                 "updatedAt": None,
                 "metadata_b64": json_b64_encode({"job_uuid": job_hash("vid1.mp4")})
                 },
                {"name": "vid2.mp4",
                 "id": 2,
                 "job_id": 1,
                 "status": Status.SUCCESS,
                 "updatedAt": None,
                 "metadata_b64": json_b64_encode({"job_uuid": job_hash("vid2.mp4")})
                 }
            ],
        }

        data_job = {
            "engine": "test",
            "id": 2,
            "name": "Dive 1377 with yolov5x-mbay-benthic",
            "job_type": JobType.ECS,
        }

        data_media = [
            {"name": "vid1.mp4", "id": 3, "job_id": 2, "status": Status.QUEUED, "updatedAt": None,
             "metadata_b64": json_b64_encode({"job_uuid": job_hash("vid3.mp4")})},
            {"name": "vid2.mp4", "id": 4, "job_id": 2, "status": Status.SUCCESS, "updatedAt": None,
             "metadata_b64": json_b64_encode({"job_uuid": job_hash("vid4.mp4")})},
        ]

        # # Convert the pydantic model back to a sqlalchemy model
        sqlalchemy_job = Job(**data_job)
        db.add(sqlalchemy_job)
        sqlalchemy_media = [Media(**media) for media in data_media]
        db.add(sqlalchemy_media[0])
        db.add(sqlalchemy_media[1])


def test_running_status(setup_database):
    """
    Test that a job status is running if one or more of the medias is running
    and the rest are queued
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()

        # Set the first media as RUNNING
        failed_media = job.media[0]
        failed_media.status = Status.RUNNING
        db.add(job)

    with session_maker.begin() as db:
        job_query = db.query(Job).first()
        status = get_status(job_query)

        assert status == Status.RUNNING


def test_failed_status(setup_database):
    """
    Test that a job status is failed if one of the medias is failed
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()

        # set the first media as FAILED
        failed_media = job.media[0]
        failed_media.status = Status.FAILED

        # Set the status of all the other medias to success
        for m in job.media[1:]:
            m.status = Status.SUCCESS

    with session_maker.begin() as db:
        job_query = db.query(Job).first()
        status = get_status(job_query)

        # Status should be FAILED
        assert status == Status.FAILED

        # Set back to QUEUED
        failed_media = job_query.media[0]
        failed_media.status = Status.QUEUED


def test_queued_status(setup_database):
    """
    Test that a job status is queued if any of the medias are queued
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()

        status = get_status(job)

        assert status == Status.QUEUED


def test_num_failed(setup_database):
    """
    Test that the number of failed medias is correct
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        num_failed = get_num_failed(job)

        # There should be no failed medias
        assert num_failed == 0


def test_num_completed(setup_database):
    """
    Test that the number of completed medias is correct
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        num_completed = get_num_completed(job)

        # There should be 1 completed medias
        assert num_completed == 1


def add_vid3(db: Session):
    """
    Helper function to add a new media to the database
    """
    job = db.query(Job).first()  # Get the first job
    vid1 = Media(id=3, name="vid3.mp4", status=Status.QUEUED, updatedAt=datetime.now(), job=job)
    db.add(vid1)


def test_add_one_media(setup_database):
    """
    Test adding a new media object adds 1 to the number of medias in the job
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        num_medias = len(job.media)

        add_vid3(db)

        # Verify that the number of medias has increased by 1
        job_updated = db.query(Job).first()
        assert len(job_updated.media) == num_medias + 1


def test_update_one_media(setup_database):
    """
    Test updating a media with a new media object updates the media timestamp.
    """
    with session_maker.begin() as db:
        add_vid3(db)
        time.sleep(1)  # sleep for 1 second to ensure the timestamp is different

    with session_maker.begin() as db:
        job = db.query(Job).first()
        num_medias = len(job.media)

        # Get the media with the name vid3.mp4 and update the timestamp and status to SUCCESS
        update_media(db, job, 'vid3.mp4', Status.SUCCESS)

    with session_maker.begin() as db:
        media = db.query(Media).filter(Media.name == 'vid3.mp4').first()

        # Verify that the number of medias is the same, except a newer timestamp
        job_updated = db.query(Job).first()
        media_updated = [m for m in job_updated.media if m.name == 'vid3.mp4'][0]
        assert len(job_updated.media) == num_medias
        assert media_updated.updatedAt > media.createdAt


if __name__ == '__main__':
    test_pydantic_sqlalchemy()
