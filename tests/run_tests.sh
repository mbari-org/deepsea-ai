#!/usr/bin/env bash
# Run with ./run_test.sh
# Run all test
# Prerequisites:
# 1. Install awscli, e.g. pip install awscli
# 2. Configure awscli with a valid account (aws configure) or set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
# 3. Install pytest, e.g. pip install pytest
# 4. Run deepsea-ai setup --mirror
set -x
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$(dirname "${SCRIPT_DIR}/.." )" && pwd )"
pushd $SCRIPT_DIR
export PYTHONPATH=$PYTHONPATH:$BASE_DIR

# Run the tests that do not require a valid AWS account
pytest -v test_commands_help.py
pytest -v test_config.py
pytest -v test_monitor.py
pytest -v test_process_args_dryrun.py
pytest -v test_ecsprocess_args_dryrun.py

## Run the tests that require a valid AWS account
## These tests take about 4-5 minutes each to run
pytest -v test_process.py::test_process_multiple_videos
pytest -v test_process_args.py::test_save_video
pytest -v test_process_args.py::test_classes_49

# Run the tests that require a valid AWS account and ECS cluster called public33k
pytest -v test_ecsprocess_args.py::test_default
pytest -v test_ecsprocess_args.py::test_args