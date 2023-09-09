# Test the sqlite database with pydantic
import json
import time
from datetime import datetime

from sqlalchemy.orm import Session

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import Job, PydanticJobWithMedias, PydanticJob, Media, PydanticMedia, init_db
from deepsea_ai.database.job.database_helper import json_b64_encode, json_b64_decode, get_status, get_num_failed, \
    update_media, get_num_completed
from deepsea_ai.database.job.misc import JobType, Status, job_hash

global session_maker


def setup():
    global session_maker
    cfg = Config()
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
    job.medias = [vid1, vid2]
    with session_maker.begin() as db:
        db.add(job)


def test_pydantic_sqlalchemy():
    """
    Test that the sqlalchemy models can be converted to pydantic models and back
    """
    global session_maker
    with session_maker.begin() as db:
        job = db.query(Job).first()
        pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)
        data = pydantic_job_with_medias.dict()
        # Remove the timestamps as they are not in the sqlalchemy model
        del data['createdAt']
        for media in data['medias']:
            del media['createdAt']

        assert data == {
            "engine": "test",
            "id": 1,
            "name": "Dive 1377 with yolov5x-mbay-benthic",
            "job_type": JobType.ECS,
            "medias": [
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


def test_running_status():
    """
    Test that a job status is running if one or more of the medias is running
    and the rest are queued
    """
    global session_maker
    with session_maker.begin() as db:
        job = db.query(Job).first()

        # Set the first media as RUNNING
        failed_media = job.medias[0]
        failed_media.status = Status.RUNNING
        db.add(job)
        db.commit()

    with session_maker.begin() as db:
        job_query = db.query(Job).first()
        status = get_status(job_query)

        # Status should be RUNNING
        assert status == Status.RUNNING


def test_failed_status():
    """
    Test that a job status is failed if one of the medias is failed
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()

        # set the first media as FAILED
        failed_media = job.medias[0]
        failed_media.status = Status.FAILED

        # Set the status of all the other medias to success
        for m in job.medias[1:]:
            m.status = Status.SUCCESS

        db.add(job)

        job_query = db.query(Job).first()
        status = get_status(job_query)

        # Status should be FAILED
        assert status == Status.FAILED


def test_queued_status():
    """
    Test that a job status is queued if all the medias are queued
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()

        status = get_status(job)

    # Status should be QUEUED
    assert status == Status.QUEUED


def test_num_failed():
    """
    Test that the number of failed medias is correct
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        num_failed = get_num_failed(job)

        # There should be no failed medias
        assert num_failed == 0


def test_num_completed():
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


def test_add_one_media():
    """
    Test adding a new media object adds 1 to the number of medias in the job
    """
    with session_maker.begin() as db:
        job = db.query(Job).first()
        job_p = PydanticJobWithMedias.from_orm(job)
        num_medias = len(job_p.medias)

        add_vid3(db)

        # Verify that the number of medias has increased by 1
        job_updated = db.query(Job).first()
        job_p_updated = PydanticJobWithMedias.from_orm(job_updated)
        assert len(job_p_updated.medias) == num_medias + 1


def test_update_one_media():
    """
    Test updating a media with a new media object updates the media timestamp.
    """
    with session_maker.begin() as db:
        add_vid3(db)
        time.sleep(1)  # sleep for 1 second to ensure the timestamp is different
        job = db.query(Job).first()
        job_p = PydanticJobWithMedias.from_orm(job)
        num_medias = len(job_p.medias)

        # Get the media with the name vid3.mp4 and update the timestamp and status to SUCCESS
        update_media(db, job, 'vid3.mp4', Status.SUCCESS)

        media = db.query(Media).filter(Media.name == 'vid3.mp4').first()

        # Verify that the number of medias is the same, except a newer timestamp
        job_updated = db.query(Job).first()
        job_p_updated = PydanticJobWithMedias.from_orm(job_updated)
        media_updated = [m for m in job_p_updated.medias if m.name == 'vid3.mp4'][0]
        assert len(job_p_updated.medias) == num_medias
        assert media_updated.updatedAt > media.createdAt


if __name__ == '__main__':
    test_pydantic_sqlalchemy()
