# Test the process command of the CLI with a single video, multiple videos, and different arguments
import subprocess
import tarfile
import tempfile
import pytest

from click.testing import CliRunner
from pathlib import Path

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import init_db

from deepsea_ai.__main__ import cli
from deepsea_ai.config import config as cfg
from deepsea_ai.logger import CustomLogger

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

# Set up the logger
CustomLogger(output_path=Path.cwd() / 'logs', output_prefix=__name__)

def setup():
    cfg = Config()
    # Reset the database
    init_db(cfg, reset=True)


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

@pytest.mark.skipif(not AWS_AVAILABLE, reason="This test is excluded because it requires a valid AWS account")
def test_save_video():
    runner = CliRunner()
    """Test that the process command works when passing arguments with a single video"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --save-vid --imgsz 640"'

    video = next(video_path.rglob('*.mp4'))  # Get the first video in the test directory and use it as the input
    out_s3 = f'{test_track_s3}/{video.stem.lower()}_with_0.1_conf_iou_.4/'  # Create the output S3 path
    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # Clean up the output S3 bucket

    result = runner.invoke(cli, ['process',
                                 '--input', video.as_posix(),
                                 '--job', f'Pytest Ventana {video.stem} with 0.1 conf iou .4 with save-vid',
                                 '--input-s3', test_video_s3,
                                 '--model-s3', test_model_s3,
                                 '--output-s3', out_s3,
                                 '--args', args])
    assert result.exit_code == 0
    assert '1 tracks saved' in result.output

    # Verify that the video and track were saved to S3; the track should be in a .tar.gz file
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])
        assert len(list(Path(tmpdir).rglob('*.tar.gz'))) == 1
        assert Path(tmpdir).rglob('*.tar.gz').__next__().stat().st_size > 0  # check that the tar.gz file is not empty
        # Verify that a video was saved with the --save-vid option
        # Video is in the tar.gz file, so extract it and verify that it is a video with a .mp4 extension
        subprocess.run(['tar', '-xzf', Path(tmpdir).rglob('*.tar.gz').__next__().as_posix(), '-C', tmpdir])
        assert len(list(Path(tmpdir).rglob('*.mp4'))) == 1

    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])


@pytest.mark.skipif(not AWS_AVAILABLE, reason="This test is excluded because it requires a valid AWS account")
def test_classes_49():
    runner = CliRunner()
    """Test that the process command works when passing arguments with a single video and only including class index 49=Paragoria"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640 --classes 49"'

    video = next(video_path.rglob('*.mp4'))  # Get the first video in the test directory and use it as the input
    out_s3 = f'{test_track_s3}/{video.stem.lower()}_with_0.1_conf_iou_.4_with_class_49'  # Create the output S3 path
    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # Clean up the S3 bucket

    result = runner.invoke(cli, ['process',
                                 '--input', video.as_posix(),
                                 '--job',
                                 f'Pytest Ventana {video.stem} with 0.1 conf iou .4 agnostic-nms with class 49',
                                 '--input-s3', test_video_s3,
                                 '--model-s3', test_model_s3,
                                 '--output-s3', out_s3,
                                 '--args', args])
    assert result.exit_code == 0

    # Only including 49=Paragoria should result in 0 tracks saved because the model detects and tracks it as
    # Paragorgia arborea, which is class 48
    assert '0 tracks saved' in result.output

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(['aws', 's3', 'sync', out_s3, tmpdir])  # Sync the S3 bucket to the local temp directory
        assert len(list(Path(tmpdir).rglob('*.tar.gz'))) == 1  # verify that one tar.gz file was saved
        assert Path(tmpdir).rglob('*.tar.gz').__next__().stat().st_size > 0  # check that the tar.gz file is not empty

        # Open the tar and verify that no .json files have the name  Paragorgia arborea
        with tarfile.open(Path(tmpdir).rglob('*.tar.gz').__next__().as_posix(), 'r:gz') as tar:
            tar.extractall(tmpdir, members=[member for member in tar.getmembers() if member.name.endswith('.json')])
            for f in Path(tmpdir).rglob('f*.json'):
                assert 'Paragorgia arborea' not in f.read_text()

    subprocess.run(['aws', 's3', 'rm', '--recursive', out_s3])  # Clean up the S3 bucket
