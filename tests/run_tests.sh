#!/usr/bin/env bash
# Run with ./run_test.sh
# Run all test
# Prerequisites for running the tests:
# 1. Install awscli, e.g. pip install awscli
# 2. Configure awscli with a valid account (aws configure) or set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
# 3. Run in poetry shell
# poetry shell && poetry install
# 4. Run deepsea-ai setup --mirror
# 5. ./run_test.sh
# Skip awscli installation if not running tests that require a valid AWS account
set -x
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(cd "$(dirname "${SCRIPT_DIR}/.." )" && pwd )"
pushd $SCRIPT_DIR
export PYTHONPATH=$PYTHONPATH:$BASE_DIR

# Run the tests that do not require a valid AWS account
pytest -s -v test_job_database.py::test_running_status
pytest -s -v test_job_database.py::test_failed_status
pytest -s -v test_job_database.py::test_add_one_media
pytest -s -v test_job_database.py::test_update_one_media
pytest -s -v test_commands_help.py
pytest -v test_config.py
pytest -s -v test_job_monitor.py
pytest -v test_process_args_dryrun.py
pytest -v test_ecsprocess_args_dryrun.py

### Run the tests that require a valid AWS account
### These tests take about 4-5 minutes each to run
pytest -s -v test_process.py::test_process_multiple_videos
pytest -s -v test_process.py::test_save_video
pytest -s -v test_process.py::test_classes_49

# Run the tests that require a valid AWS account and ECS clusters
# These tests take about 5-10 minutes each to run
pytest -s -v test_ecsprocess.py::test_default
pytest -s -v test_ecsprocess.py::test_args
pytest -s -v test_ecsprocess.py::test_classes_49
pytest -s -v test_ecsprocess.py::test_1280
pytest -s -v test_ecsprocess.py::test_remove_video_failure