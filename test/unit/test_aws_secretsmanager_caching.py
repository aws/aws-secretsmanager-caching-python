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
"""
Unit test suite for high-level functions in aws_secretsmanager_caching
"""

import unittest

import botocore
import pytest
from botocore.exceptions import ClientError, NoRegionError
from botocore.stub import Stubber

from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache

pytestmark = [pytest.mark.unit, pytest.mark.local]


class TestAwsSecretsManagerCaching(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self, response={}, versions=None, version_response=None):
        client = botocore.session.get_session().create_client(
            "secretsmanager", region_name="us-west-2"
        )

        stubber = Stubber(client)
        expected_params = {"SecretId": "test"}
        if versions:
            response["VersionIdsToStages"] = versions
        stubber.add_response("describe_secret", response, expected_params)
        if version_response is not None:
            stubber.add_response("get_secret_value", version_response)
        stubber.activate()
        return client

    def tearDown(self):
        pass

    def test_default_session(self):
        try:
            cache = SecretCache()
            user_agent_extra = f"AwsSecretCache/{cache.__version__}"
            user_agent = cache._client.meta.config.user_agent

            self.assertTrue(
                user_agent.find(user_agent_extra) > 0,
                f"User agent: {user_agent} ; \
                            does not include: {user_agent_extra}",
            )
        except NoRegionError:
            pass

    def test_client_stub(self):
        SecretCache(client=self.get_client())

    def test_get_secret_string_none(self):
        cache = SecretCache(client=self.get_client())
        self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_string_missing(self):
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"Name": "test"}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_string_no_current(self):
        response = {}
        versions = {"01234567890123456789012345678901": ["NOTCURRENT"]}
        version_response = {"Name": "test"}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_string_no_versions(self):
        response = {"Name": "test"}
        cache = SecretCache(client=self.get_client(response))
        self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_string_empty(self):
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_string(self):
        secret = "mysecret"
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"SecretString": secret}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string("test"))

    def test_get_secret_string_refresh(self):
        secret = "mysecret"
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"SecretString": secret}
        cache = SecretCache(
            config=SecretCacheConfig(secret_refresh_interval=1),
            client=self.get_client(response, versions, version_response),
        )
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string("test"))

    def test_get_secret_string_stage(self):
        secret = "mysecret"
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"SecretString": secret}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string("test", "AWSCURRENT"))

    def test_get_secret_string_multiple(self):
        cache = SecretCache(client=self.get_client())
        for _ in range(100):
            self.assertIsNone(cache.get_secret_string("test"))

    def test_get_secret_binary(self):
        secret = b"01010101"
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"SecretBinary": secret}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_binary("test"))

    def test_get_secret_binary_no_versions(self):
        cache = SecretCache(client=self.get_client())
        self.assertIsNone(cache.get_secret_binary("test"))

    def test_refresh_secret_now(self):
        secret = "mysecret"
        response = {}
        versions = {"01234567890123456789012345678901": ["AWSCURRENT"]}
        version_response = {"SecretString": secret}
        cache = SecretCache(
            client=self.get_client(response, versions, version_response)
        )
        secret = cache._get_cached_secret("test")
        self.assertIsNotNone(secret)

        old_refresh_time = secret._next_refresh_time

        secret = cache._get_cached_secret("test")
        self.assertTrue(old_refresh_time == secret._next_refresh_time)

        cache.refresh_secret_now("test")

        secret = cache._get_cached_secret("test")

        new_refresh_time = secret._next_refresh_time
        self.assertTrue(new_refresh_time > old_refresh_time)

    def test_get_secret_string_exception(self):
        client = botocore.session.get_session().create_client(
            "secretsmanager", region_name="us-west-2"
        )

        stubber = Stubber(client)
        cache = SecretCache(client=client)
        for _ in range(3):
            stubber.add_client_error("describe_secret")
            stubber.activate()
            self.assertRaises(ClientError, cache.get_secret_binary, "test")
