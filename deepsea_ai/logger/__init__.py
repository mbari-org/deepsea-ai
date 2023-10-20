# deepsea-ai, Apache-2.0 license
# Filename: logger/__init__.py
# Description: Logger for deepsea-ai. Logs to both a file and the console.
# Creates a global data frame to store a summary of the results.

import logging
from pathlib import Path
from datetime import datetime as dt

import pandas as pd

LOGGER_NAME = "DSEAAI"
DEBUG = True
keys = ["job", "video", "time", "status", "message"]


class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton('SingletonMeta', (object,), {})): pass


class CustomLogger(Singleton):
    logger = None
    output_path = Path.cwd()

    def __init__(self, output_path: Path = Path.cwd(), output_prefix: str = "deepsea_ai"):
        """
        Initialize the logger
        """
        self.logger = logging.getLogger(LOGGER_NAME)
        self.logger.setLevel(logging.DEBUG)
        self.output_path = output_path
        self.output_path.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

        # default log file date to today
        now = dt.utcnow()

        # log to file
        self.log_filename = output_path / f"{output_prefix}_{now:%Y%m%d}.log"
        handler = logging.FileHandler(self.log_filename, mode="w")
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        # also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        self.logger.info(f"Logging to {self.log_filename}")

    def loggers(self) -> logging.Logger:
        return self.logger

def create_logger_file(log_path: Path, prefix: str = "deepsea_ai"):
    """
    Create a logger file
    :param log_path: Path to the log file
    """
    # create the log directory if it doesn't exist
    log_path.mkdir(parents=True, exist_ok=True)
    return CustomLogger(log_path, prefix)


def custom_logger() -> logging.Logger:
    """
    Get the logger
    """
    return logging.getLogger(LOGGER_NAME)


def err(s: str):
    custom_logger().error(s)


def info(s: str):
    custom_logger().info(s)


def debug(s: str):
    custom_logger().debug(s)


def warn(s: str):
    custom_logger().warning(s)


def exception(s: str):
    custom_logger().exception(s)


def critical(s: str):
    custom_logger().critical(s)
