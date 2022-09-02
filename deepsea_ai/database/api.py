# !/usr/bin/env python
__author__ = "Danelle Cline, Kevin Barnard"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__doc__ = '''

Deepsea-ai database connection and query largely based on the boxjelly api connector

@author: __author__
@status: __status__
@license: __license__
'''
from typing import Optional

import requests

class GraphQLError(requests.HTTPError):
    """
    Error raised when a GraphQL query fails.
    """

    @property
    def message(self):
        """
        Return the error message.
        """
        try:
            response_json = self.response.json()
            message_str = response_json['error']['message']
            return message_str
        except (requests.JSONDecodeError, KeyError):
            return self.response.text

class DeepSeaAIClient:
    """
    Deep Sea AI GraphQL API client.
    """

    def __init__(self, url: str):
        """
        Initialize DeepSeaAI API client.
        """
        self._url = None
        self.url = url

        self._session = requests.Session()

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, url: str):
        self._url = url.rstrip('/')

    def execute(self, query: str, **variables):
        """
        Execute a GraphQL query.
        """
        data = {
            'query': query,
            'variables': variables,
        }

        response = self._session.post(
            self.url,
            json=data,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise GraphQLError(e) from e

        return response.json()
