# Test the process command of the CLI
from pathlib import Path

import pytest
from click.testing import CliRunner
from deepsea_ai.__main__ import cli

# Get the path of this file
video_path = Path(__file__).parent / 'data'


@pytest.mark.exclude
def test_some_feature():
    # Your test code here
    pass
