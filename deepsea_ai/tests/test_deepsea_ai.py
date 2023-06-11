import os

def test_config():
    os.environ['SAGEMAKER_ROLE']="arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-ExecutionRole-20201231T123456"
    from deepsea_ai.config.config import Config
    c = Config()
    assert c.get_role() is not None
