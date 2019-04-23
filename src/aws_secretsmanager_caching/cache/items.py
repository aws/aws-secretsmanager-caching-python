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
"""Secret cache items"""

import threading
from abc import ABCMeta, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from random import randint

from .lru import LRUCache


class SecretCacheObject:  # pylint: disable=too-many-instance-attributes
    """Secret cache object that handles the common refresh logic."""

    __metaclass__ = ABCMeta

    def __init__(self, config, client, secret_id):
        """Construct the secret cache object.

        :type config: aws_secretsmanager_caching.SecretCacheConfig
        :param config: Configuration for the cache.

        :type client: botocore.client.BaseClient
        :param client: The 'secretsmanager' boto client.

        :type secret_id: str
        :param secret_id: The secret identifier to cache.
        """
        self._lock = threading.RLock()
        self._config = config
        self._client = client
        self._secret_id = secret_id
        self._result = None
        self._exception = None
        self._exception_count = 0
        self._refresh_needed = True
        self._next_retry_time = None

    def _is_refresh_needed(self):
        """Determine if the cached object should be refreshed.

        :rtype: bool
        :return: True if the object should be refreshed.
        """
        if self._refresh_needed:
            return True
        if self._exception is None:
            return False
        if self._next_retry_time is None:
            return False
        return self._next_retry_time <= datetime.utcnow()

    @abstractmethod
    def _execute_refresh(self):
        """Perform the refresh of the cached object.

        :rtype: object
        :return: The cached result of the refresh.
        """

    @abstractmethod
    def _get_version(self, version_stage):
        """Get a cached secret version based on the given stage.

        :type version_stage: str
        :param version_stage: The version stage being requested.

        :rtype: object
        :return: The associated cached secret version.
        """

    def __refresh(self):
        """Refresh the cached object when needed.

        :rtype: None
        :return: None
        """
        if not self._is_refresh_needed():
            return
        self._refresh_needed = False
        try:
            self.__set_result(self._execute_refresh())
            self._exception = None
            self._exception_count = 0
        except Exception as e:  # pylint: disable=broad-except
            self._exception = e
            delay = self._config.exception_retry_delay_base * (
                self._config.exception_retry_growth_factor ** self._exception_count
            )
            self._exception_count += 1
            delay = min(delay, self._config.exception_retry_delay_max)
            self._next_retry_time = datetime.utcnow() + timedelta(milliseconds=delay)

    def get_secret_value(self, version_stage=None):
        """Get the cached secret value for the given version stage.

        :type version_stage: str
        :param version_stage: The requested secret version stage.

        :rtype: object
        :return: The cached secret value.
        """
        if not version_stage:
            version_stage = self._config.default_version_stage
        with self._lock:
            self.__refresh()
            value = self._get_version(version_stage)
            if not value and self._exception:
                raise self._exception
            return deepcopy(value)

    def __get_result(self):
        """Get the stored result using a hook if present"""
        if self._config.secret_cache_hook is None:
            return self._result

        return self._config.secret_cache_hook.get(self._result)

    def __set_result(self, result):
        """Store the given result using a hook if present"""
        if self._config.secret_cache_hook is None:
            self._result = result

        self._result = self._config.secret_cache_hook.put(result)

class SecretCacheItem(SecretCacheObject):
    """The secret cache item that maintains a cache of secret versions."""

    def __init__(self, config, client, secret_id):
        """Construct a secret cache item.

        :type config: aws_secretsmanager_caching.SecretCacheConfig
        :param config: Configuration for the cache.

        :type client: botocore.client.BaseClient
        :param client: The 'secretsmanager' boto client.

        :type secret_id: str
        :param secret_id: The secret identifier to cache.
        """
        super(SecretCacheItem, self).__init__(config, client, secret_id)
        self._versions = LRUCache(10)
        self._next_refresh_time = datetime.utcnow()

    def _is_refresh_needed(self):
        """Determine if the cached item should be refreshed.

        :rtype: bool
        :return: True if a refresh is needed.
        """
        if super(SecretCacheItem, self)._is_refresh_needed():
            return True
        if self._exception:
            return False
        return self._next_refresh_time <= datetime.utcnow()

    @staticmethod
    def _get_version_id(result, version_stage):
        """Get the version id for the given version stage.

        :type: dict
        :param result: The result of the DescribeSecret request.

        :type version_stage: str
        :param version_stage: The version stage being requested.

        :rtype: str
        :return: The associated version id.
        """
        if not result:
            return None
        if "VersionIdsToStages" not in result:
            return None
        ids = [key for (key, value) in result["VersionIdsToStages"].items() if version_stage in value]
        if not ids:
            return None
        return ids[0]

    def _execute_refresh(self):
        """Perform the actual refresh of the cached secret information.

        :rtype: dict
        :return: The result of the DescribeSecret request.
        """
        result = self._client.describe_secret(SecretId=self._secret_id)
        ttl = self._config.secret_refresh_interval
        self._next_refresh_time = datetime.utcnow() + timedelta(seconds=randint(round(ttl / 2), ttl))
        return result

    def _get_version(self, version_stage):
        """Get the version associated with the given stage.

        :type version_stage: str
        :param version_stage: The version stage being requested.

        :rtype: dict
        :return: The cached secret for the given version stage.
        """
        version_id = self._get_version_id(self.__get_result(), version_stage)
        if not version_id:
            return None
        version = self._versions.get(version_id)
        if version:
            return version.get_secret_value()
        self._versions.put_if_absent(version_id, SecretCacheVersion(self._config, self._client, self._secret_id,
                                                                    version_id))
        return self._versions.get(version_id).get_secret_value()


class SecretCacheVersion(SecretCacheObject):
    """Secret cache object for a secret version."""

    def __init__(self, config, client, secret_id, version_id):
        """Construct the cache object for a secret version.

        :type config: aws_secretsmanager_caching.SecretCacheConfig
        :param config: Configuration for the cache.

        :type client: botocore.client.BaseClient
        :param client: The 'secretsmanager' boto client.

        :type secret_id: str
        :param secret_id: The secret identifier to cache.

        :type version_id: str
        :param version_id: The version identifier.
        """
        super(SecretCacheVersion, self).__init__(config, client, secret_id)
        self._version_id = version_id

    def _execute_refresh(self):
        """Perform the actual refresh of the cached secret version.

        :rtype: dict
        :return: The result of GetSecretValue for the version.
        """
        return self._client.get_secret_value(SecretId=self._secret_id, VersionId=self._version_id)

    def _get_version(self, version_stage):
        """Get the cached version information for the given stage.

        :type version_stage: str
        :param version_stage: The version stage being requested.

        :rtype: dict
        :return: The cached GetSecretValue result.
        """
        return self.__get_result()
