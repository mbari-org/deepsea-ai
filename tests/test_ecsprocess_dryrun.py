# Test the ecsprocess arguments in dryrun mode
from click.testing import CliRunner
from pathlib import Path

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.database import init_db
from deepsea_ai.__main__ import cli
from deepsea_ai.logger import CustomLogger

# Set up the logger
CustomLogger(output_path=Path.cwd() / 'logs', output_prefix=__name__)

# Get the path of this file
video_path = Path(__file__).parent / 'data'


def setup():
    cfg = Config()
    # Reset the database
    init_db(cfg, reset=True)


def test_process_args():
    runner = CliRunner()
    """Test that the process command works in dry-run mode when passing arguments"""
    args = '"--conf-thres=0.1 --iou-thres=0.4 --max-det=100 --agnostic-nms --imgsz 640"'
    result = runner.invoke(cli, ['ecsprocess',
                                 '--dry-run',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest public33k model dry-run',
                                 '--cluster', 'public33k',
                                 '--args', args])
    assert result.exit_code == 0


def test_process_no_args():
    runner = CliRunner()
    """Test that the process command works in dry-run mode no arguments"""
    result = runner.invoke(cli, ['ecsprocess',
                                 '--dry-run',
                                 '-u',
                                 '--input', video_path.as_posix(),
                                 '--job', 'Pytest public33k model no args dry-run',
                                 '--cluster', 'public33k'])
    assert result.exit_code == 0
