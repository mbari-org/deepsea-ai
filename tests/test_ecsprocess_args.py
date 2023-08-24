# Test the ecsprocess arguments
from pathlib import Path

import pytest
from click.testing import CliRunner
from deepsea_ai.__main__ import cli

# Get the path of this file
video_path = Path(__file__).parent / 'data'


@pytest.mark.skip(reason="This test is excluded because it requires a valid ECS cluster")
def test_process_args():
    runner = CliRunner()
    """Test that the process command works in dry-run mode when passing arguments"""
    args = '"--conf-thres=0.5 --iou-thres=0.01 --max-det=100"'
    result = runner.invoke(cli, ['ecsprocess', '-u',
                                 '--input', video_path,
                                 '--job', 'Test public33k model',
                                 '--cluster', 'public33k',
                                 '--args', args])

    assert result.exit_code == 0
