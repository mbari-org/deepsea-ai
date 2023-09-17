# Test the ecsprocess command
import subprocess
import tarfile
import tempfile

import boto3
import pytest
import time
from click.testing import CliRunner
from pathlib import Path

from deepsea_ai.commands.monitor import Monitor
from deepsea_ai.commands.monitor_utils import fetch_and_parse
from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import init_db, Job, Status
from deepsea_ai.database.job.database_helper import get_status

from deepsea_ai.__main__ import cli
from deepsea_ai.config import config as cfg
from deepsea_ai.logger import CustomLogger

# Set up the logger
CustomLogger(output_path=Path.cwd() / 'logs', output_prefix=__name__)

# Get the path of this file
video_path = Path(__file__).parent / 'data'

# Get the model and test data paths
default_config = cfg.Config()
test_model_s3 = default_config('aws', 'model')  # s3 uri to the model
test_video_s3 = default_config('aws', 'videos')  # s3 uri to save the video to
test_track_s3 = default_config('aws', 'tracks')  # s3 uri to save the track to

# Check if an AWS account is configured by checking if it can access the model with the default credentials
AWS_AVAILABLE = False
if default_config.get_account():
    AWS_AVAILABLE = True

# True if there is a valid ECS cluster
ECS_AVAILABLE = False

# The name of the ECS cluster to use
cluster_640_name = 'yv5'
cluster_1280_name = 'Megadetector'

global session_maker


def get_resources(cluster: str) -> dict:
    """Get the resources for a cluster"""
    resources = default_config.get_resources(cluster)
    if resources:
        return resources
    return None


if get_resources(cluster_640_name) and get_resources(cluster_1280_name):
    ECS_AVAILABLE = True


def clean_s3(bucket_name: str):
    s3 = boto3.client('s3')

    print(f"Deleting all files in '{bucket_name}'")
    objects = s3.list_objects_v2(Bucket=bucket_name)

    if 'Contents' in objects:
        for obj in objects['Contents']:
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])


def purge_queue(queue_name: str, region: str, account: int):
    sqs = boto3.client('sqs')

    print(f'Clearing SQS {queue_name}')
    queue_url = f'https://sqs.{region}.amazonaws.com/{account}/{queue_name}'

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=10
        )

        if 'Messages' in response:
            for message in response['Messages']:
                receipt_handle = message['ReceiptHandle']

                # Delete the message
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
        else:
            break


@pytest.fixture
def setup_database_and_reset_cluster():
    global session_maker
    cfg = Config()
    account = cfg.get_account()
    region = cfg.get_region()
    # Reset the database
    session_maker = init_db(cfg, reset=True)
    reset(region, account)
    yield
    # Reset the database
    session_maker = init_db(cfg, reset=True)
    reset(region, account)


def reset(region, account):
    """Reset the resources"""
    # Remove all jobs from the database
    with session_maker.begin() as db:
        db.query(Job).delete()

    for c in [cluster_640_name, cluster_1280_name]:
        resources = get_resources(c)
        # Clear the S3 buckets and SQS queues
        if resources:
            # Purge the SQS queues; this is only allowed once every 60 seconds
            for s in ['VIDEO_QUEUE', 'TRACK_QUEUE', 'DEAD_QUEUE']:
                purge_queue(resources[s], region, account)

        if ECS_AVAILABLE and AWS_AVAILABLE:
            clean_s3(resources['TRACK_BUCKET'])
            clean_s3(resources['VIDEO_BUCKET'])


def check_task_up(cluster_arn: str) -> bool:
    ecs = boto3.client('ecs')
    try:
        response = ecs.list_tasks(cluster=cluster_arn)

        # Check if there are tasks running in the cluster
        if 'taskArns' in response:
            task_arns = response['taskArns']

            if task_arns:
                print(f'Tasks running in cluster {cluster_arn}:')
                for task_arn in task_arns:
                    print(task_arn)
                return True
            else:
                print(f'No tasks running in cluster {cluster_arn}')
                return False
        else:
            print(f'No tasks running in cluster {cluster_arn}')
            return False
    except Exception as e:
        print(f'Failed to list tasks in cluster {cluster_arn}: {e}')
        return False


def verify_task_up(cluster_name: str):
    """Check if a task is running in the cluster"""

    # Get the cluster arn
    ecs = boto3.client('ecs')
    response = ecs.list_clusters()
    cluster_arns = response['clusterArns']
    cluster_arn = [arn for arn in cluster_arns if cluster_name in arn][0]

    # Check for the auto-scaling to start and instance and run a task; when the cluster is first started,
    # it takes a while to start the task
    num_tries = 20
    while not check_task_up(cluster_arn) and num_tries > 0:
        print(f'Waiting for the task to run in the ECS cluster {cluster_name}. {num_tries} tries remaining')
        time.sleep(30)
        num_tries -= 1

    assert check_task_up(cluster_arn) is True


def verify_job_complete(cluster_name: str):
    """Verify that the job completed successfully"""
    resources = get_resources(cluster_name)

    # Wait for the output to be queued to TRACK_QUEUE
    client = boto3.client('sqs')
    num_tries = 20
    while len(fetch_and_parse(client, resources['TRACK_QUEUE'])) != 3 and num_tries > 0:
        print(f'Waiting for the output to be queued to TRACK_QUEUE. {num_tries} tries remaining')
        time.sleep(30)
        num_tries -= 1

    # Check that the tar.gz files were created
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', f"s3://{resources['TRACK_BUCKET']}", tmpdir])
        assert len(list(Path(tmpdir).rglob('*.tracks.tar.gz'))) == 3  # There should be 3 track .tar.gz files


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_args(setup_database_and_reset_cluster):
    """Test that the ecsprocess command works when passing arguments"""
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    job_name = f'Pytest ECS Ventana Dive 4361 with 0.01 conf iou .4 agnostic-nms {time.time()}'
    print(f'Running job {job_name}...')
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', job_name,
                                 '--cluster', cluster_640_name,
                                 '--args', args])
    assert result.exit_code == 0

    # Wait for the task to start and verify that it completed successfully
    verify_task_up(cluster_640_name)
    verify_job_complete(cluster_640_name)


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_default(setup_database_and_reset_cluster):
    """Test that the ecsprocess command works with defaults"""
    runner = CliRunner()
    job_name = f'Pytest ECS Ventana Dive 4361 with default args {time.time()}'
    print(f'Running job {job_name}...')
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', job_name,
                                 '--cluster', cluster_640_name])
    assert result.exit_code == 0

    # Wait for the task to start and verify that it completed successfully
    verify_task_up(cluster_640_name)
    verify_job_complete(cluster_640_name)


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account")
def test_classes_49(setup_database_and_reset_cluster):
    """Test that the process command works when passing arguments with a single video and only including class index
    49=Paragoria"""
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640 --classes 49"'
    job_name = f'Pytest ECS Ventana Dive 4361 with 0.01 conf iou .4 agnostic-nms {time.time()}'
    video = next(video_path.rglob('*.mp4'))  # Get the first video in the test directory and use it as the input
    print(f'Running job {job_name}...')
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video.as_posix(),
                                 '--job', job_name,
                                 '--cluster', cluster_640_name,
                                 '--args', args])
    assert result.exit_code == 0

    # Wait for the task to start and verify that it completed successfully
    verify_task_up(cluster_640_name)
    time.sleep(120)
    resources = get_resources(cluster_640_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', f"s3://{resources['TRACK_BUCKET']}",
                        tmpdir])  # Sync the S3 bucket to the local temp directory
        assert len(list(Path(tmpdir).rglob('*.tar.gz'))) == 1  # verify that one tar.gz file was saved
        assert Path(tmpdir).rglob('*.tar.gz').__next__().stat().st_size > 0  # check that the tar.gz file is not empty
        # Open the tar and verify that no .json files have the name  Paragorgia arborea which is class 48
        with tarfile.open(Path(tmpdir).rglob('*.tar.gz').__next__().as_posix(), 'r:gz') as tar:
            tar.extractall(tmpdir, members=[member for member in tar.getmembers() if member.name.endswith('.json')])
            for f in Path(tmpdir).rglob('f*.json'):
                assert 'Paragorgia arborea' not in f.read_text()


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account")
def test_remove_video_failure(setup_database_and_reset_cluster):
    """  Test after a job is successfully submitted and video files are subsequently removed from S3, the job fails """
    resources = get_resources(cluster_640_name)
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    job_name = f'Pytest ECS Ventana Dive 4361 with 0.01 conf iou .4 agnostic-nms {time.time()}'
    print(f'Running job {job_name}...')
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', job_name,
                                 '--cluster', cluster_640_name,
                                 '--args', args])
    assert result.exit_code == 0

    # Remove the video files from S3
    subprocess.run(['aws', 's3', 'rm', f"s3://{resources['VIDEO_BUCKET']}", '--recursive'])

    # # Wait for the task to start and monitor the task until timeout
    verify_task_up(cluster_640_name)
    m = Monitor(session_maker, Path.cwd(), resources, update_period=5)
    m.start()
    m.join(timeout=240)

    # Check that the job failed
    with session_maker.begin() as db:
        job = db.query(Job).filter(
            Job.name == job_name).first()
        assert get_status(job) == Status.FAILED


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account")
def test_1280(setup_database_and_reset_cluster):
    """ Test larger image size 1280x1280 model works """
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 1280"'
    job_name = f'Pytest 1280x1280 model ECS Ventana Dive 4361 with 0.01 conf iou .4 agnostic-nms {time.time()}'
    print(f'Running job {job_name}...')
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', job_name,
                                 '--cluster', cluster_1280_name,
                                 '--args', args])
    assert result.exit_code == 0

    # Wait for the task to start and verify that it completed successfully
    verify_task_up(cluster_1280_name)
    verify_job_complete(cluster_1280_name)
