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
Unit test suite for decorators module
"""
import json
import unittest

import botocore
from aws_secretsmanager_caching.decorators import InjectKeywordedSecretString, InjectSecretString
from aws_secretsmanager_caching.secret_cache import SecretCache
from botocore.stub import Stubber


class TestAwsSecretsManagerCachingInjectKeywordedSecretStringDecorator(unittest.TestCase):

    def get_client(self, response={}, versions=None, version_response=None):
        client = botocore.session.get_session().create_client('secretsmanager', region_name='us-west-2')
        stubber = Stubber(client)
        expected_params = {'SecretId': 'test'}
        if versions:
            response['VersionIdsToStages'] = versions
        stubber.add_response('describe_secret', response, expected_params)
        if version_response is not None:
            stubber.add_response('get_secret_value', version_response)
        stubber.activate()
        return client

    def test_valid_json(self):
        secret = {
            'username': 'secret_username',
            'password': 'secret_password'
        }

        secret_string = json.dumps(secret)

        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret_string}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        @InjectKeywordedSecretString(secret_id='test', cache=cache, func_username='username', func_password='password')
        def function_to_be_decorated(func_username, func_password, keyworded_argument='foo'):
            self.assertEqual(secret['username'], func_username)
            self.assertEqual(secret['password'], func_password)
            self.assertEqual(keyworded_argument, 'foo')
            return 'OK'

        self.assertEqual(function_to_be_decorated(), 'OK')

    def test_valid_json_with_mixed_args(self):
        secret = {
            'username': 'secret_username',
            'password': 'secret_password'
        }

        secret_string = json.dumps(secret)

        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret_string}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        @InjectKeywordedSecretString(secret_id='test', cache=cache, arg2='username', arg3='password')
        def function_to_be_decorated(arg1, arg2, arg3, arg4='bar'):
            self.assertEqual(arg1, 'foo')
            self.assertEqual(secret['username'], arg2)
            self.assertEqual(secret['password'], arg3)
            self.assertEqual(arg4, 'bar')

        function_to_be_decorated('foo')

    def test_valid_json_with_no_secret_kwarg(self):
        secret = {
            'username': 'secret_username',
            'password': 'secret_password'
        }

        secret_string = json.dumps(secret)

        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret_string}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        @InjectKeywordedSecretString('test', cache=cache, func_username='username', func_password='password')
        def function_to_be_decorated(func_username, func_password, keyworded_argument='foo'):
            self.assertEqual(secret['username'], func_username)
            self.assertEqual(secret['password'], func_password)
            self.assertEqual(keyworded_argument, 'foo')

        function_to_be_decorated()

    def test_invalid_json(self):
        secret = 'not json'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        with self.assertRaises((RuntimeError, json.decoder.JSONDecodeError)):
            @InjectKeywordedSecretString(secret_id='test', cache=cache, func_username='username',
                                         func_passsword='password')
            def function_to_be_decorated(func_username, func_password, keyworded_argument='foo'):
                return

            function_to_be_decorated()

    def test_missing_key(self):
        secret = {'username': 'secret_username'}
        secret_string = json.dumps(secret)
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret_string}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        with self.assertRaises((RuntimeError, ValueError)):
            @InjectKeywordedSecretString(secret_id='test', cache=cache, func_username='username',
                                         func_passsword='password')
            def function_to_be_decorated(func_username, func_password, keyworded_argument='foo'):
                return

            function_to_be_decorated()


class TestAwsSecretsManagerCachingInjectSecretStringDecorator(unittest.TestCase):

    def get_client(self, response={}, versions=None, version_response=None):
        client = botocore.session.get_session().create_client('secretsmanager', region_name='us-west-2')
        stubber = Stubber(client)
        expected_params = {'SecretId': 'test'}
        if versions:
            response['VersionIdsToStages'] = versions
        stubber.add_response('describe_secret', response, expected_params)
        if version_response is not None:
            stubber.add_response('get_secret_value', version_response)
        stubber.activate()
        return client

    def test_string(self):
        secret = 'not json'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        @InjectSecretString('test', cache)
        def function_to_be_decorated(arg1, arg2, arg3):
            self.assertEqual(arg1, secret)
            self.assertEqual(arg2, 'foo')
            self.assertEqual(arg3, 'bar')
            return 'OK'

        self.assertEqual(function_to_be_decorated('foo', 'bar'), 'OK')

    def test_string_with_additional_kwargs(self):
        secret = 'not json'
        response = {}
        versions = {
            '01234567890123456789012345678901': ['AWSCURRENT']
        }
        version_response = {'SecretString': secret}
        cache = SecretCache(client=self.get_client(response, versions, version_response))

        @InjectSecretString('test', cache)
        def function_to_be_decorated(arg1, arg2, arg3):
            self.assertEqual(arg1, secret)
            self.assertEqual(arg2, 'foo')
            self.assertEqual(arg3, 'bar')

        function_to_be_decorated(arg2='foo', arg3='bar')
