# Test the ecsprocess arguments
import json
import subprocess
import tarfile
import tempfile
import pytest
import time
from click.testing import CliRunner
from pathlib import Path

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import init_db

from deepsea_ai.__main__ import cli
from deepsea_ai.config import config as cfg

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

cluster = 'ssyv5'

resources = default_config.get_resources(cluster)
if resources:
    # Check if the ECS cluster is available and get the full cluster name
    result = subprocess.run("aws ecs list-clusters", shell=True, stdout=subprocess.PIPE, text=True)
    output = json.loads(result.stdout)
    cluster_name = [c.split("/")[1] for c in output["clusterArns"] if cluster in c]
    if len(cluster_name) == 0:
        print(f"Cluster {cluster} is not available")
    else:
        cluster_name = cluster_name[0]
    print(f"Cluster name: {cluster_name}")
    ECS_AVAILABLE = True
    out_s3 = f"s3://{resources['TRACK_BUCKET']}"  # s3 uri to save the track to -this is setup automatically by the CDK stack

def setup():
    cfg = Config()
    # Reset the database
    init_db(cfg, reset=True)
    """Setup the test. Purges the s3 bucket and SQS queues"""
    if ECS_AVAILABLE and AWS_AVAILABLE and out_s3:
        subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # clean up the S3 bucket
        # Purge the SQS queues; this is only allowed once every 60 seconds
        print(f'Clearing {resources["VIDEO_QUEUE"]}')
        subprocess.run(['aws', 'sqs', 'purge-queue', '--queue-url', resources['VIDEO_QUEUE']])

def check_task_up():
    # Check for any running tasks
    result = subprocess.run(f"aws ecs list-tasks --cluster {cluster_name}",
                            shell=True,
                            stdout=subprocess.PIPE,
                            text=True)
    output = json.loads(result.stdout)
    print(f"Running tasks: {output}")
    if output["taskArns"]:
        return True
    return False


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_args():
    """Test that the ecsprocess command works when passing arguments"""
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    # print the command to run
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest ECS Ventana Dive 4361 with 0.01 conf iou .4 agnostic-nms',
                                 '--cluster', cluster,
                                 '--args', args])
    assert result.exit_code == 0

    # Check for the auto-scaling to start and instance and run a task; when the cluster is first started,
    # it takes a while to start the task
    num_tries = 20
    while not check_task_up() and num_tries > 0:
        print(f'Waiting for the task to run in the ECS cluster {cluster}. {num_tries} tries remaining')
        time.sleep(30)
        num_tries -= 1

    assert check_task_up()

    print('ECS cluster is up. Waiting for processing to complete...')
    time.sleep(90) # small delay to allow processing to complete
    # Check that the tar.gz files were created
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])
        assert len(list(Path(tmpdir).rglob('*.tracks.tar.gz'))) == 3  # There should be 3 tracks


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_default():
    """Test that the ecsprocess command works with defaults"""
    runner = CliRunner()
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest ECS Ventana Dive 4361 with default args',
                                 '--cluster', cluster])
    assert result.exit_code == 0

    # Check that the tracks were created
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])
        assert len(list(Path(tmpdir).rglob('*.tracks.tar.gz'))) == 3  # There should be 3 tracks


@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account")
def test_classes_49():
    """Test that the process command works when passing arguments with a single video and only including class index
    49=Paragoria"""
    runner = CliRunner()
    args = '"--conf-thres=0.01 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640 --classes 49"'
    video = next(video_path.rglob('*.mp4'))  # Get the first video in the test directory and use it as the input
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video.as_posix(),
                                 '--job', 'Pytest ECS Ventana Dive 4361 with custom args and class 49',
                                 '--cluster', cluster,
                                 '--args', args])
    assert result.exit_code == 0

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])  # Sync the S3 bucket to the local temp directory
        assert len(list(Path(tmpdir).rglob('*.tar.gz'))) == 1  # verify that one tar.gz file was saved
        assert Path(tmpdir).rglob('*.tar.gz').__next__().stat().st_size > 0  # check that the tar.gz file is not empty
        # Open the tar and verify that no .json files have the name  Paragorgia arborea which is class 48
        with tarfile.open(Path(tmpdir).rglob('*.tar.gz').__next__().as_posix(), 'r:gz') as tar:
            tar.extractall(tmpdir, members=[member for member in tar.getmembers() if member.name.endswith('.json')])
            for f in Path(tmpdir).rglob('f*.json'):
                assert 'Paragorgia arborea' not in f.read_text()
