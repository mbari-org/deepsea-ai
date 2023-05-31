# !/usr/bin/env python
__author__ = "Danelle Cline, Duane Edgington"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Process a collection of videos; assumes videos have previously been uploaded with the upload command

@author: __author__
@status: __status__
@license: __license__
'''

import os
import inspect
import boto3
import json
import requests
from datetime import datetime
from pathlib import Path

from deepsea_ai.config import config as cfg
from deepsea_ai.commands.upload_tag import get_prefix
from deepsea_ai.logger import debug, info, err, warn, exception, keys
from deepsea_ai.logger.job_cache import JobStatus, JobCache


_session = requests.Session()

