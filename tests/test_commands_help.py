# Test that the help message runs for all commands: process, ecsprocess, split, train, and monitor
import pytest
from click.testing import CliRunner
from deepsea_ai.__main__ import cli

commands = [
    ["process", "-h"],
    ["ecsprocess", "-h"],
    ["split", "-h"],
    ["monitor", "-h"],
]


def test_help():
    runner = CliRunner()
    for command in commands:
        result = runner.invoke(cli, command, obj={})
        print("Command {} exit code {}".format(command[0], result.exit_code))
        assert result.exit_code == 0
