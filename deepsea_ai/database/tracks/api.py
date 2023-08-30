# deepsea-ai, Apache-2.0 license
# Filename: database/api.py
# Description: Track database connection and query API

from deepsea_ai.logger import debug, exception
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
            debug(f"GraphQL response: {response_json}")
            message_str = response_json['error']['message']
            debug(f"GraphQL error: {message_str}")
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
            exception(f'GraphQL query failed: {e}')
            raise GraphQLError(e) from e

        return response.json()
