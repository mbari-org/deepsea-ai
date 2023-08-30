# Test the sqlite database with pydantic
import time
from datetime import datetime

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import Job, PydanticJob, Media, PydanticJobWithMedias, reset_local_db, init_db
from deepsea_ai.database.job.database_helper import get_status, get_num_failed, update_media
from deepsea_ai.database.job.misc import JobType, Status, job_hash

global db

def setup():
    global db
    cfg = Config()
    # Reset the database
    db = reset_local_db(cfg)
    name = "Dive 1377 with yolov5x-mbay-benthic"
    job = Job(id=1,
              cluster="test",
              name=name,
              job_type=JobType.ECS)
    vid1 = Media(name="vid1.mp4", status=Status.QUEUED)
    vid2 = Media(name="vid2.mp4", status=Status.QUEUED)
    job.medias = [vid1, vid2]
    db.add(job)
    db.commit()


def test_pydantic_sqlalchemy():
    """
    Test that the sqlalchemy models can be converted to pydantic models and back
    """

    job = db.query(Job).first()
    pydantic_job = PydanticJob.from_orm(job)
    data = pydantic_job.dict()

    name = "Dive 1377 with yolov5x-mbay-benthic"
    job_uuid = job_hash(name)

    # Remove the created at
    data.pop('createdAt')

    assert data == {
        "id": 1,
        "uuid": job_uuid,
        "name": name,
        "job_type": JobType.ECS
    }

    pydantic_job_with_medias = PydanticJobWithMedias.from_orm(job)
    data = pydantic_job_with_medias.dict()

    # Remove the created and updated times
    data.pop('createdAt')
    data.pop('updatedAt')

    assert data == {
        "id": 1,
        "uuid": job_uuid,
        "name": name,
        "job_type": JobType.ECS,
        "medias": [
            {"name": "vid1.mp4", "id": 1, "job_id": 1, "status": Status.QUEUED},
            {"name": "vid2.mp4", "id": 2, "job_id": 1, "status": Status.SUCCESS}
        ],
    }


def test_running_status():
    """
    Test that a job status is running if one or more of the medias is running
    and the rest are queued
    """
    job = db.query(Job).first()

    # Set the first media as RUNNING
    failed_media = job.medias[0]
    failed_media.status = Status.RUNNING
    db.add(job)
    db.commit()

    job_query = db.query(Job).first()
    status = get_status(job_query)

    # Status should be RUNNING
    assert status == Status.RUNNING


def test_failed_status():
    """
    Test that a job status is failed if one of the medias is failed
    """
    job = db.query(Job).first()

    # set the first media as FAILED
    failed_media = job.medias[0]
    failed_media.status = Status.FAILED

    # Set the status of all the other medias to success
    for m in job.medias[1:]:
        m.status = Status.SUCCESS

    db.add(job)
    db.commit()

    job_query = db.query(Job).first()
    status = get_status(job_query)

    # Status should be FAILED
    assert status == Status.FAILED


def test_queued_status():
    """
    Test that a job status is queued if all the medias are queued
    """
    job = db.query(Job).first()

    status = get_status(job)

    # Status should be QUEUED
    assert status == Status.QUEUED


def test_num_failed():
    """
    Test that the number of failed medias is correct
    """
    job = db.query(Job).first()
    num_failed = get_num_failed(job)

    # There should be no failed medias
    assert num_failed == 0


def test_num_completed():
    """
    Test that the number of completed medias is correct
    """
    job = db.query(Job).first()
    num_completed = get_num_failed(job)

    # There should be 1 completed medias
    assert num_completed == 1


def add_vid3():
    """
    Helper function to add a new media to the database
    """
    job = db.query(Job).first()  # Get the first job
    vid1 = Media(id=3, name="vid3.mp4", status=Status.QUEUED, updatedAt=datetime.now(), job=job)
    db.add(vid1)
    db.commit()


def test_add_one_media():
    """
    Test adding a new media object adds 1 to the number of medias in the job
    """
    job = db.query(Job).first()
    job_p = PydanticJobWithMedias.from_orm(job)
    num_medias = len(job_p.medias)
    add_vid3()
    # Verify that the number of medias has increased by 1
    job_updated = db.query(Job).first()
    job_p_updated = PydanticJobWithMedias.from_orm(job_updated)
    assert len(job_p_updated.medias) == num_medias + 1


def test_update_one_media():
    """
    Test updating a media with a new media object updates the media timestamp.
    """
    add_vid3()
    time.sleep(1) # sleep for 1 second to ensure the timestamp is different
    job = db.query(Job).first()
    job_p = PydanticJobWithMedias.from_orm(job)
    num_medias = len(job_p.medias)

    # Get the media with the name vid3.mp4 and update the timestamp and status to SUCCESS
    media = update_media(db, job, 'vid3.mp4', Status.SUCCESS)

    # Verify that the number of medias is the same, except a newer timestamp
    job_updated = db.query(Job).first()
    job_p_updated = PydanticJobWithMedias.from_orm(job_updated)
    media_updated = [m for m in job_p_updated.medias if m.name == 'vid3.mp4'][0]
    assert len(job_p_updated.medias) == num_medias
    assert media_updated.updatedAt > media.createdAt


if __name__ == '__main__':
    test_pydantic_sqlalchemy()
