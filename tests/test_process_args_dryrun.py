# Test the process arguments
from pathlib import Path

from click.testing import CliRunner
from deepsea_ai.__main__ import cli

# Get the path of this file
video_path = Path(__file__).parent / 'data'


def test_process_args():
    runner = CliRunner()
    """Test that the process command works in dry-run mode when passing arguments"""
    args = '"--conf-thres=0.5 --iou-thres=0.2 --max-det=100"'
    result = runner.invoke(cli, ['process', '--input', video_path.as_posix(), '--job',
                                 'Ventana Dive 4263 with 0.5 conf with new mbari315k model',
                                 '--input-s3', 's3://902005-dev-benchmark/',
                                 '--model-s3', 's3://902005-dev-models/mbari-mb-benthic-315k/model.tar.gz',
                                 '--output-s3', 's3://902005-dev-benchmarks-out/',
                                 '--dry-run', '--args', args])
    # assert result.exit_code == 0
    assert args in result.output
