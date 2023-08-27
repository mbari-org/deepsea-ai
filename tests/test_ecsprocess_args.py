# Test the ecsprocess arguments
import subprocess

import pytest
from click.testing import CliRunner
from pathlib import Path
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

# Check if there is a valid ECS cluster
ECS_AVAILABLE = False

cluster = 'yolov5x-mbay-benthic'

resources = default_config.get_resources(cluster)
if resources:
    ECS_AVAILABLE = True
    out_s3 = f"s3://{resources['TRACK_BUCKET']}"  # s3 uri to save the track to -this is setup automatically by the CDK stack

print(f'Clearing {out_s3}')
subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # clean up the S3 bucket


#
@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_args():
    runner = CliRunner()
    """Test that the ecsprocess command works when passing arguments"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest ECS Ventana Dive 4361 with 0.1 conf iou .4 agnostic-nms',
                                 '--cluster', cluster,
                                 '--args', args])
    assert result.exit_code == 0


#
#
@pytest.mark.skipif(not AWS_AVAILABLE and not ECS_AVAILABLE,
                    reason="This test is excluded because it requires a valid AWS account and ECS cluster")
def test_default():
    runner = CliRunner()
    """Test that the ecsprocess command works when passing arguments"""
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest ECS Ventana Dive 4361 with default args',
                                 '--cluster', cluster])
    assert result.exit_code == 0  #
