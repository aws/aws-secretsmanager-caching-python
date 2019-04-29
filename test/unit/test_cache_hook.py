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

import botocore
from aws_secretsmanager_caching.cache.secret_cache_hook import SecretCacheHook
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache
from botocore.stub import Stubber


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
