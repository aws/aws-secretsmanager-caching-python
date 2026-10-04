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
Unit test suite for items module
"""
import unittest
from unittest.mock import Mock

import botocore
from aws_secretsmanager_caching.cache.secret_cache_hook import SecretCacheHook
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache
from botocore.stub import Stubber
from aws_secretsmanager_caching.cache.items import SecretCacheVersion


class DummySecretCacheHook(SecretCacheHook):
    """A dummy implementation of the SecretCacheHook abstract class for testing"""

    dict = {}

    def put(self, obj):
        if 'SecretString' in obj:
            obj['SecretString'] = obj['SecretString'] + "+hook_put"

        if 'SecretBinary' in obj:
            obj['SecretBinary'] = obj['SecretBinary'] + b'11111111'

        key = len(self.dict)
        self.dict[key] = obj
        return key

    def get(self, cached_obj):
        obj = self.dict[cached_obj]

        if 'SecretString' in obj:
            obj['SecretString'] = obj['SecretString'] + "+hook_get"

        if 'SecretBinary' in obj:
            obj['SecretBinary'] = obj['SecretBinary'] + b'00000000'

        return obj


class TestSecretCacheHook(unittest.TestCase):

    def test_initial_service_error_is_not_masked_by_hook(self):
        version_id = '01234567890123456789012345678901'
        for operation in ('describe_secret', 'get_secret_value'):
            with self.subTest(operation=operation):
                client = botocore.session.get_session().create_client(
                    'secretsmanager', region_name='us-west-2',
                    aws_access_key_id='testing', aws_secret_access_key='testing')
                hook = DummySecretCacheHook()
                config = SecretCacheConfig(secret_cache_hook=hook,
                                           exception_retry_delay_base=3600)
                cache = SecretCache(config=config, client=client)
                with Stubber(client) as stubber:
                    params = {'SecretId': 'test'}
                    if operation == 'get_secret_value':
                        stubber.add_response('describe_secret', {
                            'VersionIdsToStages': {version_id: ['AWSCURRENT']}
                        }, params)
                        params = dict(params, VersionId=version_id)
                    stubber.add_client_error(
                        operation, service_error_code='ResourceNotFoundException',
                        service_message='Secret does not exist',
                        expected_params=params)
                    for _ in range(2):
                        with self.assertRaises(client.exceptions.ResourceNotFoundException):
                            cache.get_secret_string('test')
                    stubber.assert_no_pending_responses()

    def test_failed_refresh_keeps_hook_cached_value(self):
        for token in (None, 0):
            with self.subTest(token=token):
                value = {'SecretString': 'cached value'}
                hook = Mock(spec=SecretCacheHook)
                hook.put.return_value = token
                hook.get.return_value = value
                client = Mock()
                client.get_secret_value.side_effect = [value, RuntimeError('unavailable')]
                version = SecretCacheVersion(
                    SecretCacheConfig(secret_cache_hook=hook), client, 'test', 'version')
                self.assertEqual(version.get_secret_value(), value)
                version._refresh_needed = True
                self.assertEqual(version.get_secret_value(), value)
                hook.get.assert_called_with(token)
                self.assertEqual(hook.get.call_count, 2)

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

    def test_calls_hook_string(self):
        secret = 'mysecret'
        hooked_secret = secret + "+hook_put+hook_get"
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}

        hook = DummySecretCacheHook()
        config = SecretCacheConfig(secret_cache_hook=hook)

        cache = SecretCache(config=config, client=self.get_client(response,
                                                                  versions,
                                                                  version_response))

        for _ in range(10):
            fetched_secret = cache.get_secret_string('test')
            self.assertTrue(fetched_secret.startswith(hooked_secret))

    def test_calls_hook_binary(self):
        secret = b'01010101'
        hooked_secret = secret + b'1111111100000000'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretBinary': secret}

        hook = DummySecretCacheHook()
        config = SecretCacheConfig(secret_cache_hook=hook)

        cache = SecretCache(config=config, client=self.get_client(response,
                                                                  versions,
                                                                  version_response))

        for _ in range(10):
            self.assertEqual(hooked_secret, cache.get_secret_binary('test')[0:24])
