# Test the process command of the CLI with multiple videos
import subprocess
import tempfile
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


@pytest.mark.skipif(not AWS_AVAILABLE, reason="This test is excluded because it requires a valid AWS account")
def test_process_multiple_videos():
    runner = CliRunner()
    """Test that the process command works when passing arguments with a collection of videos in a bucket"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    out_s3 = f'{test_track_s3}/Ventana_Dive_4263_with_0.1_conf_iou_.4/'
    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # clean up the S3 bucket
    result = runner.invoke(cli, ['process',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest Ventana Dive 4361 with 0.1 conf iou .4 agnostic-nms',
                                 '--input-s3', test_video_s3,
                                 '--model-s3', test_model_s3,
                                 '--output-s3', out_s3,
                                 '--args', args])
    assert result.exit_code == 0

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])  # Sync the S3 bucket to the local temp directory
        assert len(list(Path(tmpdir).rglob('*.tracks.tar.gz'))) == 3  # There should be 3 tracks

    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # Clean up the S3 bucket
