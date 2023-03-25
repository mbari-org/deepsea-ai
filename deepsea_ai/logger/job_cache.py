# Path: deepsea_ai/logger/job_cache.py
# !/usr/bin/env python
__author__ = "Danelle Cline"
__copyright__ = "Copyright 2023, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__doc__ = '''

Simple, lightweight job cache to keep track of jobs that have been run.
Can be used to generate a summary of jobs that have been run.

@author: __author__
@status: __status__
@license: __license__
'''

import boto3
import pickledb
from pathlib import Path
from typing import List
import deepsea_ai.logger as logger
from deepsea_ai.logger import info, err, debug, warn
import hashlib
from datetime import datetime as dt, datetime
from deepsea_ai import __version__


# Enum for the status of a job
class JobStatus:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    UNKNOWN = "UNKNOWN"


def job_hash(job: str) -> str:
    """
    Hash the job name and cluster to create a unique identifier for the job
    """
    md5val = hashlib.md5(job.encode('latin')).hexdigest()
    return f"{md5val[:8]}-{md5val[8:12]}-{md5val[12:16]}-{md5val[16:20]}-{md5val[20:]}".upper()


class JobCache(logger.Singleton):

    def __init__(self, output_path: Path):
        """
        Initialize the cache with the account number we are running in
        """
        # get the AWS account number
        account_number = boto3.client('sts').get_caller_identity().get('Account')

        info(f"Initializing job cache in {output_path}")
        db_file = output_path / f'job_cache_account{account_number}.db'
        if not db_file.exists():
            info(f"Creating job cache database in {output_path}")
            self.db = pickledb.PickleDB(location=db_file.as_posix(), auto_dump=True, sig=True)
        else:
            info(f"Using existing job cache database in {output_path}")
            self.db = pickledb.load(db_file.as_posix(), True)

    def create_report(self, job_name: str, output_path: Path, processor:str=None):
        """
        Create a report of the jobs that were run
        :param job_name: Name of the job
        :param output_path: Path to write the report to
        :param processor: Name of the processor
        """
        # create the output path if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        # create a file name that replaces spaces with underscores and adds a timestamp
        job_report_name = f"{job_name.replace(' ', '_')}_{dt.utcnow().strftime('%Y%m%d')}.txt"
        output_path = output_path / job_report_name
        info(f"JobCache: Creating job report for {job_name} in {output_path}")

        # fetch the job id if available
        job_uuid = job_hash(job_name)
        if not self.db.get(job_uuid):
            warn(f"Unable to find job {job_name} in cache")
            return
        created_time = self.db.get(job_uuid)[3]
        last_update = self.db.get(job_uuid)[4]
        num_media = len(self.get_all_media_names(job_name))
        job_report_name = f"{job_name}, Total media: {num_media}, Created at: {created_time}, Last update: {last_update} "
        if self.db.get('deepsea_ai_db'):
            from deepsea_ai.database import api, queries
            try:
                database = api.DeepSeaAIClient(self.db.get('deepsea_ai_db'))
                jobs = database.execute(queries.GET_JOB_SUMMARY, job_uuid=job_hash(f'{processor}{job_name}'))
                if len(jobs['data']['jobs']) > 0:
                    job_id = jobs['data']['jobs'][0]['id']
                    job_detail = jobs['data']['jobs'][0]['detail']
                    debug(f"JobCache: Found job id: {job_id}")
                    job_report_name += f", Job: {job_id}, {job_detail}"
            except Exception as e:
                err(f"Unable to fetch job id from deepsea_ai database: {e}")

        with open(output_path.as_posix(), 'w') as f:
            f.write(f"DeepSea-AI {__version__}\n")
            f.write(f"Job: {job_report_name}\n")
            f.write(f"==============================================================================================\n")
            f.write(f"Index, Media, Last Updated, Status\n")

            # Write the status of each media file in the job
            media_names = self.get_all_media_names(job_name)
            for idx, name in enumerate(sorted(media_names)):
                media = self.get_media(name, job_name)
                f.write(f"{idx}, {name}, {media[2]}, {media[3]}\n")

    def get_all_media_names(self, job_name: str) -> List[str]:
        """
        Get all the media file names associated with a job
        """
        job_uuid = job_hash(job_name)
        return [self.db.get(key)[0] for key in self.db.getall() if self.db.get(key)[1] == job_uuid]

    def set_media(self, job_name: str, media_file: str, status: str = JobStatus.RUNNING, update_dt: str = None):
        """
        Add a video file to the cache, updating the status of the media if it already exists
        :param job_name: The name of the job
        :param media_file: The video file
        :param update_dt: The date and time the video file was updated
        :param status: The status of the job
        """
        job_uuid = job_hash(job_name)
        media_uuid = job_hash(media_file + job_name)
        if update_dt is None:
            update_dt = dt.utcnow().strftime("%Y%m%dT%H%M%S")
        else:
            update_dt = datetime.strptime(update_dt, "%Y%m%dT%H%M%S").strftime("%Y%m%dT%H%M%S")
        if status == JobStatus.FAIL or status == JobStatus.UNKNOWN:
            err(f"Updating video file {media_file} to job {job_name} in cache with status {status}")
        else:
            info(f"Updating video file {media_file} to job {job_name} in cache with status {status}")

        self.db.set(media_uuid, [media_file, job_uuid, update_dt, status])

    def set_job(self, job_name: str, cluster: str, video_files: List[str], status: JobStatus):
        """
        Add a video to job in the cache. A job is uniquely identified by the job name
        :param job_name: The name of the job
        :param cluster: The cluster the job is running on
        :param video_files: The video files associated with the job
        :param status: The status of the job
        """
        # default to current time
        timestamp = dt.utcnow()

        job_uuid = job_hash(job_name)
        j = self.db.get(job_uuid)
        if j:
            # get the video files and add the new video files if they are not already in the list
            new_video_files = j[2]
            for v in new_video_files:
                if v not in video_files:
                    video_files.append(v)
                    info(f"JobCache: Added video file {v} to job {job_name} running on {cluster}")

        # update the job
        if status == JobStatus.FAIL:
            err(f"Updating job {job_name} running on {cluster} in cache status to {status}")
        else:
            info(f"Updating job {job_name} running on {cluster} in cache status to {status}")
        job = self.db.get(job_uuid)
        updated_timestamp = dt.utcnow().strftime("%Y%m%dT%H%M%S")
        if job: # if the job exists, keep the created timestamp
            created_timestamp = job[3]
        else:
            created_timestamp = dt.utcnow().strftime("%Y%m%dT%H%M%S")
        self.db.set(job_uuid, [job_name, cluster, video_files,
                               created_timestamp,
                               updated_timestamp,
                               status])

        info(f"Added job {job_name} running on {cluster} to cache")

    def get_job(self, job_name: str) -> List[str]:
        """
        Get a job from the cache. A job is uniquely identified by the hash of the job name
        """
        job_uuid = job_hash(job_name)
        return self.db.get(job_uuid)

    def get_media(self, media_name: str, job_name: str) -> List[str]:
        """
        Get a media from the cache. A media is uniquely identified by the hash of the media name
        :param media_name: The name of the media file
        :param job_name: The name of the job
        """
        media_uuid = job_hash(media_name + job_name)
        return self.db.get(media_uuid)

    def get_num_completed(self, job_name: str) -> int:
        """
        Get the number of completed media files in a job
        :param job_name: The name of the job
        """
        job_uuid = job_hash(job_name)
        completed = 0
        for video_uuid in self.db.getall():
            if self.db.get(video_uuid)[1] == job_uuid:
                if self.db.get(video_uuid)[3] == JobStatus.SUCCESS:
                    completed += 1
        return completed

    def get_num_failed(self, job_name: str) -> int:
        """
        Get the number of failed media files in a job
        :param job_name: The name of the job
        """
        job_uuid = job_hash(job_name)
        failed = 0
        for video_uuid in self.db.getall():
            if self.db.get(video_uuid)[1] == job_uuid:
                if self.db.get(video_uuid)[3] == JobStatus.FAIL:
                    failed += 1
        return failed

    def remove_job(self, job_name: str):
        """
        Remove a job from the cache. A job is uniquely identified by the hash of the job name
        """
        job_uuid = job_hash(job_name)
        self.db.rem(job_uuid)

        # get all the video files associated with the job and remove them from the cache
        to_remove = []
        for video_uuid in self.db.getall():
            if self.db.get(video_uuid)[1] == job_uuid:
                to_remove.append(video_uuid)

        for video_uuid in to_remove:
            self.db.rem(video_uuid)
        info(f"JobCache: Removed job {job_name} from cache")

    def get_all(self) -> List[List[str]]:
        """
        Get all jobs from the cache
        """
        return self.db.getall()

    def clear(self):
        """
        Clear the cache
        """
        self.db.deldb()
        self.db.dump()
        info("Cleared cache")

    def set_database(self, db: str):
        """
        Set the endpoint for the deepsea-ai track database to use (optional)
        """
        self.db.set('deepsea_ai_db', db)


if __name__ == '__main__':
    logger.create_logger_file(Path.cwd(), "test")
    jc = JobCache(Path.cwd())
    name = "strongsort-yolov5-mbari315k-DocRicketts dive 1373 with mbari315k model"
    jc.set_job(name, JobStatus.UNKNOWN, ["vid1.mp4", "vid2.mp4", "vid3.mp4"], JobStatus.RUNNING)
    info(f'Getting job {name} {jc.get_job(name)}')

    # add more videos to the job
    jc.set_job(name, JobStatus.UNKNOWN, ["vid4.mp4", "vid5.mp4", "vid6.mp4"], JobStatus.RUNNING)
    info(f'Getting job {name} {jc.get_job(name)}')

    # remove and clear them
    jc.remove_job(name)
    info(jc.get_job(name))
    jc.clear()
    info(jc.get_all())

    # add a video to the cache
    jc.set_job(name, JobStatus.UNKNOWN, ["vid1.mp4", "vid2.mp4", "vid3.mp4"], JobStatus.RUNNING)
    info(f'Getting job {name} {jc.get_job(name)}')

    # update the status of the video to RUNNING
    jc.set_media(name, "vid1.mp4", JobStatus.RUNNING)

    # update the status of the video to SUCCESS
    jc.set_media(name, "vid1.mp4", JobStatus.SUCCESS)

    # update the status of the video to FAIL
    jc.set_media(name, "vid1.mp4", JobStatus.FAIL)

    # update the status of the video to INFO
    jc.set_media(name, "vid1.mp4", JobStatus.QUEUED)

    # update the status of the video to UNKNOWN
    jc.set_media(name, "vid1.mp4", JobStatus.UNKNOWN)

    # update the status of the video to SUCCESS
    jc.set_media(name, "vid1.mp4", JobStatus.SUCCESS)
    jc.set_media(name, "vid2.mp4", JobStatus.SUCCESS)
    jc.set_media(name, "vid3.mp4", JobStatus.SUCCESS)
    jc.set_media(name, "vid4.mp4", JobStatus.SUCCESS)
    jc.set_media(name, "vid5.mp4", JobStatus.FAIL)

    # get all media files for the job
    medias = jc.get_all_media_names(name)
    info(f"Media files for job {name}: {medias}")

    # get the status of each media file
    for m in medias:
        info(f"Status of {m}: {jc.get_media(m, name)}")  # should be SUCCESS except for vid5.mp4

    # create a report for the job that has all the media files and their status
    jc.create_report(name, Path.cwd())

    # clean-up
    jc.remove_job(name)
