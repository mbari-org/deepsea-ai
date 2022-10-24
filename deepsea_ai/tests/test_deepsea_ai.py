from deepsea_ai import __version__


def test_version():
    assert __version__ == "1.3.3"


def test_config():
    from deepsea_ai.config.config import Config
    c = Config()
    assert c.get_role() is not None