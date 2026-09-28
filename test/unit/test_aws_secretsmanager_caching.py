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
import os
import socket
import time
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import botocore
import botocore.config
import pytest
from botocore.exceptions import ClientError, NoRegionError, ReadTimeoutError
from botocore.stub import Stubber

from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache

pytestmark = [pytest.mark.unit, pytest.mark.local]


@contextmanager
def hung_endpoint():
    """A listening socket that is never read. It completes the TCP handshake
    but never answers, like an endpoint that hangs after connecting."""
    with socket.socket() as hung:
        hung.bind(('127.0.0.1', 0))
        hung.listen()
        yield hung


class TestAwsSecretsManagerCaching(unittest.TestCase):

    def setUp(self):
        pass

    def get_client(self, response={}, versions=None, version_response=None):
        client = botocore.session.get_session().create_client(
            'secretsmanager', region_name='us-west-2')

        stubber = Stubber(client)
        expected_params = {'SecretId': 'test'}
        if versions:
            response['VersionIdsToStages'] = versions
        stubber.add_response('describe_secret', response, expected_params)
        if version_response is not None:
            stubber.add_response('get_secret_value', version_response)
        stubber.activate()
        return client

    def tearDown(self):
        pass

    def test_default_session(self):
        try:
            cache = SecretCache()
            user_agent_extra = f"AwsSecretCache/{cache.__version__}"
            user_agent = cache._client.meta.config.user_agent

            self.assertTrue(user_agent.find(user_agent_extra) > 0,
                            f"User agent: {user_agent} ; \
                            does not include: {user_agent_extra}")
        except NoRegionError:
            pass

    # Only a region and dummy credentials, so the developer's own AWS
    # settings (profile, proxy, endpoint overrides) can't change these tests.
    ISOLATED_ENV = {
        'AWS_DEFAULT_REGION': 'us-west-2',
        'AWS_ACCESS_KEY_ID': 'akid',
        'AWS_SECRET_ACCESS_KEY': 'secret',
        'AWS_CONFIG_FILE': os.devnull,
        'AWS_SHARED_CREDENTIALS_FILE': os.devnull,
    }

    def test_default_client_timeouts(self):
        with patch.dict(os.environ, self.ISOLATED_ENV, clear=True):
            config = SecretCache()._client.meta.config
        self.assertEqual(config.connect_timeout, 2)
        self.assertEqual(config.read_timeout, 2)

    def test_client_keeps_own_timeouts(self):
        with patch.dict(os.environ, self.ISOLATED_ENV, clear=True):
            client = botocore.session.get_session().create_client(
                'secretsmanager', region_name='us-west-2',
                config=botocore.config.Config(connect_timeout=7, read_timeout=30))
        config = SecretCache(client=client)._client.meta.config
        self.assertEqual(config.connect_timeout, 7)
        self.assertEqual(config.read_timeout, 30)

    def hung_cache(self, hung, retries):
        """Build a cache with its default client, pointed at the hung socket
        and limited to the given number of retries."""
        create_client = botocore.session.Session.create_client

        def create_hung_client(session, *args, **kwargs):
            kwargs['endpoint_url'] = f'http://127.0.0.1:{hung.getsockname()[1]}'
            kwargs['config'] = kwargs['config'].merge(botocore.config.Config(retries={'max_attempts': retries}))
            return create_client(session, *args, **kwargs)

        with patch.dict(os.environ, self.ISOLATED_ENV, clear=True), \
                patch.object(botocore.session.Session, 'create_client', create_hung_client):
            return SecretCache()

    # The value itself is checked by test_default_client_timeouts. These use a
    # shorter one so the suite stays fast.
    @patch('aws_secretsmanager_caching.secret_cache.DEFAULT_READ_TIMEOUT', 0.5)
    @patch('aws_secretsmanager_caching.secret_cache.DEFAULT_CONNECT_TIMEOUT', 0.5)
    def seconds_to_time_out(self, retries):
        with hung_endpoint() as hung:
            cache = self.hung_cache(hung, retries)
            start = time.monotonic()
            with self.assertRaises(ReadTimeoutError):
                cache.get_secret_string('test')
            return time.monotonic() - start

    def test_default_client_gives_up_on_hung_endpoint(self):
        elapsed = self.seconds_to_time_out(retries=0)
        self.assertGreaterEqual(elapsed, 0.4)
        self.assertLess(elapsed, 3)

    def test_default_client_retries_timed_out_attempt(self):
        # Two 0.5 second attempts, plus up to 1 second of backoff between them.
        elapsed = self.seconds_to_time_out(retries=1)
        self.assertGreaterEqual(elapsed, 0.9)
        self.assertLess(elapsed, 4)

    def test_client_stub(self):
        SecretCache(client=self.get_client())

    def test_get_secret_string_none(self):
        cache = SecretCache(client=self.get_client())
        self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_string_missing(self):
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'Name': 'test'}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_string_no_current(self):
        response = {}
        versions = {
            '01234567890123456789012345678901': ['NOTCURRENT']
        }
        version_response = {'Name': 'test'}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_string_no_versions(self):
        response = {'Name': 'test'}
        cache = SecretCache(client=self.get_client(response))
        self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_string_empty(self):
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_string(self):
        secret = 'mysecret'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string('test'))

    def test_get_secret_string_refresh(self):
        secret = 'mysecret'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(
            config=SecretCacheConfig(secret_refresh_interval=1),
            client=self.get_client(response,
                                   versions,
                                   version_response))
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string('test'))

    def test_get_secret_string_stage(self):
        secret = 'mysecret'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_string('test',
                                                             'AWSCURRENT'))

    def test_get_secret_string_multiple(self):
        cache = SecretCache(client=self.get_client())
        for _ in range(100):
            self.assertIsNone(cache.get_secret_string('test'))

    def test_get_secret_binary(self):
        secret = b'01010101'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretBinary': secret}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        for _ in range(10):
            self.assertEqual(secret, cache.get_secret_binary('test'))

    def test_get_secret_binary_no_versions(self):
        cache = SecretCache(client=self.get_client())
        self.assertIsNone(cache.get_secret_binary('test'))

    def test_refresh_secret_now(self):
        secret = 'mysecret'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response,
                                                   versions,
                                                   version_response))
        secret = cache._get_cached_secret('test')
        self.assertIsNotNone(secret)

        old_refresh_time = secret._next_refresh_time

        secret = cache._get_cached_secret('test')
        self.assertTrue(old_refresh_time == secret._next_refresh_time)

        self.assertTrue(cache.refresh_secret_now('test'))

        secret = cache._get_cached_secret('test')

        new_refresh_time = secret._next_refresh_time
        self.assertTrue(new_refresh_time > old_refresh_time)

    def test_get_secret_string_exception(self):
        client = botocore.session.get_session().create_client(
            'secretsmanager', region_name='us-west-2')

        stubber = Stubber(client)
        cache = SecretCache(client=client)
        for _ in range(3):
            stubber.add_client_error('describe_secret')
            stubber.activate()
            self.assertRaises(ClientError, cache.get_secret_binary, 'test')
