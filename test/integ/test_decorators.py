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

import json
from uuid import uuid4

import botocore
import botocore.session
import pytest
from aws_secretsmanager_caching.decorators import InjectKeywordedSecretString, InjectSecretString
from aws_secretsmanager_caching.secret_cache import SecretCache


class TestDecoratorsInteg:
    fixture_prefix = 'python_decorator_integ_test_'
    uuid_suffix = uuid4().hex

    @pytest.fixture(scope='module')
    def client(self):
        yield botocore.session.get_session().create_client('secretsmanager', region_name='us-east-1')

    @pytest.fixture
    def json_secret(self, request, client):
        name = f"{self.fixture_prefix}{request.function.__name__}{self.uuid_suffix}"
        secret_data = {"username": "test_user", "password": "test_pass", "host": "localhost"}

        secret = client.create_secret(Name=name, SecretString=json.dumps(secret_data))
        yield secret, secret_data
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    @pytest.fixture
    def string_secret(self, request, client):
        name = f"{self.fixture_prefix}{request.function.__name__}{self.uuid_suffix}"
        secret_value = "simple_secret_value"

        secret = client.create_secret(Name=name, SecretString=secret_value)
        yield secret, secret_value
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_inject_keyworded_secret_string(self, client, json_secret):
        secret, secret_data = json_secret
        cache = SecretCache(client=client)

        @InjectKeywordedSecretString(secret_id=secret['Name'], cache=cache,
                                     func_username='username', func_password='password')
        def test_function(func_username, func_password):
            return func_username, func_password

        username, password = test_function()
        assert username == secret_data['username']
        assert password == secret_data['password']

    def test_inject_secret_string(self, client, string_secret):
        secret, secret_value = string_secret
        cache = SecretCache(client=client)

        @InjectSecretString(secret['Name'], cache)
        def test_function(injected_secret, other_arg):
            return injected_secret, other_arg

        result_secret, result_arg = test_function("test_arg")
        assert result_secret == secret_value
        assert result_arg == "test_arg"

    def test_inject_secret_string_class_method(self, client, string_secret):
        secret, secret_value = string_secret
        cache = SecretCache(client=client)

        class TestClass:
            @InjectSecretString(secret['Name'], cache)
            def method(self, injected_secret):
                return injected_secret

        test_instance = TestClass()
        result = test_instance.method()
        assert result == secret_value
