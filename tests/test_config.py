import os
from pathlib import Path

from deepsea_ai.logger import CustomLogger

# Set up the logger
CustomLogger(output_path=Path.cwd() / 'logs', output_prefix=__name__)

def test_arn():
    os.environ['SAGEMAKER_ROLE']="arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-ExecutionRole-20201231T123456"
    from deepsea_ai.config.config import Config
    c = Config()
    assert c.get_role() is not None
