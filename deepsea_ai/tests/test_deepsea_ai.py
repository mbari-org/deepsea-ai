def test_config():
    from deepsea_ai.config.config import Config
    c = Config()
    assert c.get_role() is not None