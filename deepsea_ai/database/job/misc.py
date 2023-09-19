# deepsea-ai, Apache-2.0 license
# Filename: database/job/misc.py
# Description: Misc. job database functions

import hashlib


class Status:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"


class JobType:
    SAGEMAKER = "SAGEMAKER"
    ECS = "ECS"
    DOCKER = "DOCKER"


def job_hash(job: str) -> str:
    """
    Hash the job name and cluster to create a unique identifier for the job
    """
    md5val = hashlib.md5(job.encode('latin')).hexdigest()
    return f"{md5val[:8]}-{md5val[8:12]}-{md5val[12:16]}-{md5val[16:20]}-{md5val[20:]}".upper()
