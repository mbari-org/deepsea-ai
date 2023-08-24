# Test the ecsprocess arguments
from pathlib import Path

from click.testing import CliRunner
from deepsea_ai.__main__ import cli

# Get the path of this file
video_path = Path(__file__).parent / 'data'


def test_process_args_dryrun():
    runner = CliRunner()
    """Test that the process command works in dry-run mode when passing arguments"""
    args = '"--conf-thres=0.5 --iou-thres=0.2 --max-det=100"'
    result = runner.invoke(cli, ['ecsprocess',
                                 '-u',
                                 '--input', video_path,
                                 '--job',  'Test model33k',
                                 '--cluster', 'public33k',
                                 '--dry-run',
                                 '--args', args])

    assert result.exit_code == 0
    # Check that the arguments are in the output
    assert 'max-det' in result.output
