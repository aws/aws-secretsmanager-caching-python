# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""High level AWS Secrets Manager caching client."""

from copy import deepcopy

from importlib.metadata import version, PackageNotFoundError
import botocore.config
import botocore.session

from .cache import LRUCache, SecretCacheItem
from .config import SecretCacheConfig


class SecretCache:
    """Secret Cache client for AWS Secrets Manager secrets"""

    try:
        __version__ = version("aws_secretsmanager_caching")
    except PackageNotFoundError:
        __version__ = "0.0.0"

    def __init__(self, config=SecretCacheConfig(), client=None):
        """Construct a secret cache using the given configuration and
        AWS Secrets Manager boto client.

        :type config: aws_secretsmanager_caching.SecretCacheConfig
        :param config: Secret cache configuration

        :type client: botocore.client.BaseClient
        :param client: botocore 'secretsmanager' client
        """

        self._client = client
        self._config = deepcopy(config)
        self._cache = LRUCache(max_size=self._config.max_cache_size)
        boto_config = botocore.config.Config(
            **{
                "user_agent_extra": f"AwsSecretCache/{SecretCache.__version__}",
            }
        )
        if self._client is None:
            self._client = botocore.session.get_session().create_client(
                "secretsmanager", config=boto_config
            )

    def _get_cached_secret(self, secret_id):
        """Get a cached secret for the given secret identifier.

        :type secret_id: str
        :param secret_id: The secret identifier

        :rtype: aws_secretsmanager_caching.cache.SecretCacheItem
        :return: The associated cached secret item
        """
        secret = self._cache.get(secret_id)
        if secret is not None:
            return secret
        self._cache.put_if_absent(
            secret_id,
            SecretCacheItem(
                config=self._config, client=self._client, secret_id=secret_id
            ),
        )
        return self._cache.get(secret_id)

    def get_secret_string(self, secret_id, version_stage=None):
        """Get the secret string value from the cache.

        :type secret_id: str
        :param secret_id: The secret identifier

        :type version_stage: str
        :param version_stage: The stage for the requested version.

        :rtype: str
        :return: The associated secret string value
        """
        secret = self._get_cached_secret(secret_id).get_secret_value(version_stage)
        if secret is None:
            return secret
        return secret.get("SecretString")

    def get_secret_binary(self, secret_id, version_stage=None):
        """Get the secret binary value from the cache.

        :type secret_id: str
        :param secret_id: The secret identifier

        :type version_stage: str
        :param version_stage: The stage for the requested version.

        :rtype: bytes
        :return: The associated secret binary value
        """
        secret = self._get_cached_secret(secret_id).get_secret_value(version_stage)
        if secret is None:
            return secret
        return secret.get("SecretBinary")

    def refresh_secret_now(self, secret_id):
        """Immediately refresh the secret in the cache.

        :type secret_id: str
        :param secret_id: The secret identifier
        """
        self._get_cached_secret(secret_id).refresh_secret_now()
