# Test job monitoring with sqlite database
from pathlib import Path

from deepsea_ai.commands.monitor import Monitor
from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import Job, Media, init_db
from deepsea_ai.database.job.misc import Status, JobType
from datetime import datetime as dt

global session_maker


def setup():
    global session_maker
    cfg = Config()
    # Clear the reports directory
    report_path = Path.cwd() / 'reports'
    if report_path.exists():
        for f in report_path.glob('*'):
            f.unlink()

    # Reset the database
    session_maker = init_db(cfg, reset=True)


def monitor_job(resources: dict):
    # Create a monitoring thread
    report_path = Path.cwd() / 'reports'
    m = Monitor(session_maker, report_path, resources, sim=True)
    m.start()
    # wait for the thread to finish
    m.join()

    # check that the report is there and is not empty
    print(f'Checking if {report_path} exists and is not empty')
    assert report_path.exists() is True
    # check if there is a single .txt report with size > 0
    report = list(report_path.glob('*.txt'))
    assert len(report) == 1
    assert report[0].stat().st_size > 0


def test_monitor_docker():
    """
    Test monitoring a docker job returns an error as docker jobs are not supported
    """
    with session_maker.begin() as db:
        resources = {'PROCESSOR': 'test'}
        # Create a job
        name = "Dive 1377 with yolov5x-mbay-benthic"
        job = Job(id=1,
                  engine="yolov5x-mbay-benthic30dkfh2=1jt",
                  name=name,
                  job_type=JobType.DOCKER)
        db.add(job)
        db.commit()
        monitor_job(resources)


def test_monitor_report():
    """
    Test if a report is created
    """
    with session_maker.begin() as db:
        name = "Dive 1377 with yolov5x-mbay-benthic"
        job = Job(id=1,
                  engine="yolov5x-mbay-benthic30dkfh2=1jt",
                  name=name,
                  job_type=JobType.ECS)
        vid1 = Media(name="vid1.mp4", status=Status.QUEUED, updatedAt=dt.utcnow())
        vid2 = Media(name="vid2.mp4", status=Status.QUEUED, updatedAt=dt.utcnow())
        vid3 = Media(name="vid3.mp4", status=Status.RUNNING, updatedAt=dt.utcnow())
        job.medias = [vid1, vid2, vid3]
        db.add(job)
        db.commit()
        db.close()

        resources = {'PROCESSOR': 'test'}
        monitor_job(resources)
