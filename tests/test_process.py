# Test the process command of the CLI
from pathlib import Path

import pytest
from click.testing import CliRunner
from deepsea_ai.__main__ import cli

# Get the path of this file
video_path = Path(__file__).parent / 'data'


## @pytest.mark.exclude

def test_process_args():
    runner = CliRunner()
    """Test that the process command works when passing arguments"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --save-vid --imgsz 640"'
    result = runner.invoke(cli, ['process',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Ventana Dive 4263 with 0.1 conf iou .4 with default',
                                 '--input-s3', 's3://902005-dev-benchmark/',
                                 '--model-s3', 's3://902005-dev-models/mbari-mb-benthic-315k/model.tar.gz',
                                 '--output-s3', 's3://902005-dev-benchmarks-out/',
                                 '--args', args])
    # assert result.exit_code == 0
    assert args in result.output
