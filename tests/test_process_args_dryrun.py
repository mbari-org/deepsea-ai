# Test the process arguments in dryrun mode
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


def test_save_video():
    runner = CliRunner()
    """Test that the process command works when passing arguments with a single video"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --save-vid --imgsz 640"'

    video = next(video_path.rglob('*.mp4'))  # Get the first video in the test directory and use it as the input
    out_s3 = f'{test_track_s3}/{video.stem.lower()}_with_0.1_conf_iou_.4_with_default'  # Create the output S3 path

    result = runner.invoke(cli, ['process',
                                 '--dry-run',
                                 '--input', video_path.as_posix(),
                                 '--job', f'Pytest Ventana {video.stem} with 0.1 conf iou .4 with default dry-run',
                                 '--input-s3', test_video_s3,
                                 '--model-s3', test_model_s3,
                                 '--output-s3', out_s3,
                                 '--args', args])

    assert result.exit_code == 0
