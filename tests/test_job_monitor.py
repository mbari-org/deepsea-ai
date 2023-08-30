# Test job monitoring with sqlite database
from pathlib import Path

from deepsea_ai.commands.monitor import Monitor
from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import Job, Media, PydanticJobWithMedias, reset_local_db
from deepsea_ai.database.job.misc import Status, JobType
from datetime import datetime as dt
from deepsea_ai.database.report_generator import create_report

global db

def setup():
    global db
    cfg = Config()
    # Reset the database
    db = reset_local_db(cfg)
    name = "Dive 1377 with yolov5x-mbay-benthic"
    job = Job(id=1,
              cluster="test_cluster",
              name=name,
              job_type=JobType.ECS)
    vid1 = Media(name="vid1.mp4", status=Status.QUEUED, updatedAt=dt.utcnow())
    vid2 = Media(name="vid2.mp4", status=Status.QUEUED, updatedAt=dt.utcnow())
    vid3 = Media(name="vid3.mp4", status=Status.RUNNING, updatedAt=dt.utcnow())
    job.medias = [vid1, vid2, vid3]
    db.add(job)
    db.commit()


def test_monitor_thread():
    """
    Test updating a media with a new media object updates the media timestamp.
    """

    job = db.query(Job).first()
    job_p = PydanticJobWithMedias.from_orm(job)
    resources = {'PROCESSOR': 'test'}

    job_id = job_p.id
    # Create a monitoring thread
    m = Monitor(resources, sim=True)
    m.start()
    # wait for the thread to finish
    m.join()
    create_report(job, Path.cwd())
    report_path = Path.cwd() / f"{job.name.replace(' ', '_')}_{dt.utcnow().strftime('%Y%m%d')}.txt"

    # check that the report is there and is not empty
    print(f'Checking if {report_path} exists and is not empty')
    assert report_path.exists() is True
    assert report_path.stat().st_size > 0
    # clean up
    report_path.unlink()
