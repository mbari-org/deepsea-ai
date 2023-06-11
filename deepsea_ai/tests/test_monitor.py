import os
from pathlib import Path
from datetime import datetime as dt

from deepsea_ai.commands.monitor import Monitor
from deepsea_ai.logger.job_cache import JobCache, MediaIndex, JobStatus


def test_set_job():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    # write a fake job with a few fake videos
    c.set_job("Dive1334", "yolov5-benthic33k", ["video1.mp4", "video2,mp4"], JobStatus.RUNNING)
    # check that the job is there
    assert c.get_job("Dive1334") is not None
    # clean up
    c.clear()


def test_set_media():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    # write a fake job with a few fake videos
    c.set_job("Dive1334", "yolov5-benthic33k", ["video1.mp4"], JobStatus.RUNNING)
    # set the media
    c.set_media("Dive1334", "video1.mp4", JobStatus.RUNNING)
    # check that the media is there
    assert c.get_media("video1.mp4", "Dive1334") is not None
    assert c.get_media("video1.mp4", "Dive1334")[MediaIndex.STATUS] == JobStatus.RUNNING
    # clean up
    c.clear()


def test_success_count():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    # write a fake job with a few fake videos
    c.set_job("Dive1334", "yolov5-benthic33k", ["video1.mp4", "video2,mp4"], JobStatus.RUNNING)
    # set the media
    c.set_media("Dive1334", "video1.mp4", JobStatus.SUCCESS)
    c.set_media("Dive1334", "video2.mp4", JobStatus.SUCCESS)
    # check that the media is there
    assert c.get_num_completed("Dive1334") == 2
    # clean up
    c.clear()


def test_failed_count():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    # write a fake job with a few fake videos
    c.set_job("Dive1334", "yolov5-benthic33k", ["video1.mp4", "video2,mp4"], JobStatus.RUNNING)
    # set the media
    c.set_media("Dive1334", "video1.mp4", JobStatus.SUCCESS)
    c.set_media("Dive1334", "video2.mp4", JobStatus.FAIL)
    # check that the media is there
    assert c.get_num_failed("Dive1334") == 1
    # clean up
    c.clear()


def test_remove_job():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    # write a fake job with a few fake videos
    c.set_job("Dive1334", "yolov5-benthic33k", ["video1.mp4"], JobStatus.RUNNING)
    # set the media
    c.set_media("Dive1334", "video1.mp4", JobStatus.SUCCESS)
    c.remove_job("Dive1334")
    # check that the job is gone
    assert c.get_job("Dive1334") is False
    # clean up
    c.clear()

def test_monitor_thread():
    c = JobCache(Path.cwd() / "tests" / "data" / "job_cache", True)
    job_name = "Dive1334"
    # write a fake job with a few fake videos
    c.set_job(job_name, "yolov5-benthic33k", ["video1.mp4"], JobStatus.RUNNING)
    # set the media
    c.set_media(job_name, "video1.mp4", JobStatus.SUCCESS)
    # creat a fake resource dict
    resources = {"CLUSTER": "yolov5-benthic33k"}
    # create a monitoring thread
    m = Monitor([job_name], resources, sim=True)
    m.start()
    # wait for the thread to finish
    m.join()
    c.create_report("Dive1334", Path.cwd())
    report_path = Path.cwd() / f"{job_name.replace(' ', '_')}_{dt.utcnow().strftime('%Y%m%d')}.txt"
    # check that the report is there
    assert Path.cwd() / f"{job_name.replace(' ', '_')}_{dt.utcnow().strftime('%Y%m%d')}.txt" is not None
    # clean up
    c.clear()
    report_path.unlink()
